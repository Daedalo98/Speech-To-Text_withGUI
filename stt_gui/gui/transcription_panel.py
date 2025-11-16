"""
Transcription panel: live partial text + editable sentence area.

Responsibilities:
- Show an auto-updating "live" partial transcription panel.
- Once a segment is finalized, insert it into a larger text area
  as an editable sentence, with a timestamp that is protected from edits.
- Handle right-click events to create notes.
"""

from __future__ import annotations

import re
import tkinter as tk
from typing import Callable, Optional, Tuple, List, Dict
from datetime import datetime

from .widgets import TimestampedText


class TranscriptionPanel(tk.Frame):
    """
    Panel that holds both the small live transcription area and
    the larger editable sentence area.
    """

    def __init__(
        self,
        master: Optional[tk.Misc] = None,
        on_note_created: Optional[
            Callable[[str, str, str], None]
        ] = None,  # (speaker_name, speaker_color, timestamp_str)
        **kwargs,
    ) -> None:
        """
        Initialize the transcription panel.

        :param master: Parent widget.
        :param on_note_created: Callback invoked when a note is requested.
        :param kwargs: Extra options for tk.Frame.
        """
        super().__init__(master, **kwargs)

        self._on_note_created = on_note_created

        # Currently active speaker context (name and color).
        self._active_speaker_name: str = "Unknown"
        self._active_speaker_color: str = "#000000"

        # Store the last final segment's timestamp string for notes.
        self._last_timestamp_str: str = "unknown"

        self._build_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """
        Build the UI with two main sections:
        - Live partial transcription (top).
        - Editable, timestamped sentences (bottom).
        """
        # Live transcription frame.
        live_frame = tk.LabelFrame(self, text="Live transcription")
        live_frame.pack(fill="x", padx=4, pady=4)

        self._live_label = tk.Label(live_frame, text="", anchor="w", justify="left")
        self._live_label.pack(fill="x", padx=4, pady=4)

        # Editable sentences frame.
        sentences_frame = tk.LabelFrame(self, text="Transcription")
        sentences_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._sentences_text = TimestampedText(sentences_frame)
        self._sentences_text.pack(fill="both", expand=True)

        # Bind right-click on the text area to create a note.
        self._sentences_text.bind("<Button-3>", self._on_right_click)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def update_active_speaker(self, name: str, color: str) -> None:
        """
        Update the active speaker context.

        :param name: New active speaker name.
        :param color: New active speaker color.
        """
        self._active_speaker_name = name
        self._active_speaker_color = color

    def update_live_partial(
        self,
        text: str,
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> None:
        """
        Update the live transcription label.

        :param text: Partial text to display.
        :param start_time: Optional real-world start time (UNIX seconds).
        :param end_time: Optional real-world end time (UNIX seconds).
        """
        # If no text, clear the label.
        if not text:
            self._live_label.config(text="")
            return

        # If we do not have time information (e.g., "Wait, starting..."),
        # show only the text.
        if start_time is None or end_time is None:
            self._live_label.config(text=text)
            return

        timestamp_str = self._format_timestamp(start_time, end_time)
        self._live_label.config(text=f"[{timestamp_str}] {text}")

    def add_final_sentence(
        self,
        text: str,
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> None:
        """
        Add a finalized sentence to the editable area.

        :param text: Final recognized sentence.
        :param start_time: Start time as UNIX timestamp (seconds).
        :param end_time: End time as UNIX timestamp (seconds).
        """
        timestamp_str = self._format_timestamp(start_time, end_time)
        self._last_timestamp_str = timestamp_str

        self._sentences_text.insert_sentence(
            speaker_name=self._active_speaker_name,
            speaker_color=self._active_speaker_color,
            start_time=start_time,
            end_time=end_time,
            text=text,
        )

    def get_sentences(self) -> List[Dict[str, str]]:
        """
        Extract all sentences from the transcription area in a structured form.

        Each line in the widget is of the form:
            [timestamp] SpeakerName: text...

        :return: List of dicts with keys: "timestamp", "speaker", "text".
        """
        content = self._sentences_text.get("1.0", "end-1c")
        lines = content.splitlines()

        results: List[Dict[str, str]] = []

        pattern = re.compile(r"\[(.*?)\]\s+([^:]+):\s*(.*)")

        for line in lines:
            if not line.strip():
                continue

            match = pattern.match(line)
            if not match:
                # If the line doesn't match the expected format, skip it.
                continue

            timestamp_str = match.group(1)
            speaker_name = match.group(2).strip()
            text = match.group(3)

            results.append(
                {
                    "timestamp": timestamp_str,
                    "speaker": speaker_name,
                    "text": text,
                }
            )

        return results

    # ------------------------------------------------------------------
    # Right-click note creation
    # ------------------------------------------------------------------
    def _on_right_click(self, event: tk.Event) -> None:
        """
        Handle right-click on the sentence area to create a note.

        The logic:
        - Determine the line index where the user clicked.
        - Extract timestamp and speaker from that line (if any).
        - Trigger the on_note_created callback.
        """
        index = self._sentences_text.index(f"@{event.x},{event.y}")
        line_start = f"{index.split('.')[0]}.0"
        line_end = f"{index.split('.')[0]}.end"

        line_text = self._sentences_text.get(line_start, line_end)

        # Attempt to parse the line: [timestamp] SpeakerName: text...
        timestamp_str, speaker_name = self._parse_line_header(line_text)

        if timestamp_str is None:
            timestamp_str = self._last_timestamp_str
        if speaker_name is None:
            speaker_name = self._active_speaker_name

        # Retrieve the speaker color from the tags (or default).
        speaker_color = self._get_speaker_color_for_line(line_start, speaker_name)

        if self._on_note_created is not None:
            # Create an empty note entry; the user can edit it in the notes panel.
            self._on_note_created(speaker_name, speaker_color, timestamp_str)

    def _parse_line_header(
        self,
        line_text: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse a line in the format: [timestamp] SpeakerName: text

        :param line_text: The entire line as text.
        :return: (timestamp_str, speaker_name) tuple; any element may be None.
        """
        match = re.match(r"\[(.*?)\]\s+([^:]+):", line_text)
        if not match:
            return None, None
        timestamp_str = match.group(1)
        speaker_name = match.group(2).strip()
        return timestamp_str, speaker_name

    def _get_speaker_color_for_line(
        self, line_start_index: str, speaker_name: str
    ) -> str:
        """
        Try to deduce the speaker color based on the tags near the line start.

        :param line_start_index: Text index at the line start.
        :param speaker_name: Speaker name.
        :return: Foreground color string, default black if unknown.
        """
        speaker_tag = f"speaker_{speaker_name}"
        index = line_start_index

        while True:
            # Get tags at this index.
            tags = self._sentences_text.tag_names(index)
            if speaker_tag in tags:
                # Found a character with the speaker tag; return its color.
                tag_color = self._sentences_text.tag_cget(speaker_tag, "foreground")
                if tag_color:
                    return str(tag_color)

            # Move to the next character.
            next_index = self._sentences_text.index(f"{index} + 1c")
            if next_index == index:
                break
            if next_index.split(".")[0] != line_start_index.split(".")[0]:
                # We moved to the next line; stop.
                break
            index = next_index

        return "#000000"

    # ------------------------------------------------------------------
    # Timestamp formatting (real-world time)
    # ------------------------------------------------------------------
    def _format_timestamp(
        self,
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> str:
        """
        Format timestamps as a user-friendly string based on real-world time.

        :param start_time: Start time as UNIX timestamp (seconds).
        :param end_time: End time as UNIX timestamp (seconds).
        :return: "HH:MM:SS.mmm-HH:MM:SS.mmm" or "unknown" if not available.
        """
        if start_time is None or end_time is None:
            return "unknown"

        def fmt(t: float) -> str:
            dt = datetime.fromtimestamp(t)
            return dt.strftime("%H:%M:%S.%f")[:-3]

        return f"{fmt(start_time)}-{fmt(end_time)}"

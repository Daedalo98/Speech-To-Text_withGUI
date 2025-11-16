"""
Notes and annotations panel.

This panel receives notes (typically created via right-click on the
transcription panel) and displays them with timestamps and speaker
color. It also provides a method to extract all notes in structured
form for export.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import scrolledtext
from typing import Optional, List, Dict


class NotesPanel(tk.Frame):
    """
    Simple notes panel displaying timestamped annotations.
    """

    def __init__(self, master: Optional[tk.Misc] = None, **kwargs) -> None:
        """
        Initialize the notes panel.

        :param master: Parent widget.
        :param kwargs: Extra options for tk.Frame.
        """
        super().__init__(master, **kwargs)

        # Use a ScrolledText for notes with word wrapping.
        self._text = scrolledtext.ScrolledText(self, wrap="word", width=40)
        self._text.pack(fill="both", expand=True)

    def add_note(
        self,
        speaker_name: str,
        speaker_color: str,
        timestamp_str: str,
        text: str,
    ) -> None:
        """
        Add a note with timestamp and speaker color.

        :param speaker_name: Name of the speaker.
        :param speaker_color: Color associated with the speaker.
        :param timestamp_str: Textual representation of the time interval.
        :param text: Note content.
        """
        # Format the header line for this note.
        header = f"[{timestamp_str}] {speaker_name}: "

        # Insert the header.
        start_index = self._text.index("end-1c")
        self._text.insert("end", header)
        end_index = self._text.index("end-1c")

        # Create or reuse a tag for this speaker to color the header.
        speaker_tag = f"note_speaker_{speaker_name}"
        if speaker_tag not in self._text.tag_names():
            self._text.tag_configure(speaker_tag, foreground=speaker_color)

        self._text.tag_add(speaker_tag, start_index, end_index)

        # Insert the note body and a blank line for separation.
        self._text.insert("end", text + "\n\n")
        self._text.see("end")

    def get_notes(self) -> List[Dict[str, str]]:
        """
        Extract all notes from the notes panel in a structured form.

        Notes are stored as blocks separated by blank lines, each block:
          [timestamp] SpeakerName:
          note text (possibly multi-line)

        :return: List of dicts with keys: "timestamp", "speaker", "text".
        """
        content = self._text.get("1.0", "end-1c").strip()
        if not content:
            return []

        # Split by blank lines (one or more).
        blocks = re.split(r"\n\s*\n", content)

        results: List[Dict[str, str]] = []
        header_pattern = re.compile(r"\[(.*?)\]\s+([^:]+):\s*")

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.splitlines()
            if not lines:
                continue

            header = lines[0]
            body_lines = lines[1:]

            match = header_pattern.match(header)
            if not match:
                # If we cannot parse the header, skip this block.
                continue

            timestamp_str = match.group(1)
            speaker_name = match.group(2).strip()
            note_text = "\n".join(body_lines).strip()

            results.append(
                {
                    "timestamp": timestamp_str,
                    "speaker": speaker_name,
                    "text": note_text,
                }
            )

        return results

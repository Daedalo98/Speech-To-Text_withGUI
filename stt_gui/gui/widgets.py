"""
Custom Tkinter widgets used in the GUI.

Here we define:
- TimestampedText: a ScrolledText widget that protects timestamp
  segments from editing while allowing the rest of the text to be
  freely edited, and supports speaker color tagging.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Optional
from datetime import datetime


class TimestampedText(scrolledtext.ScrolledText):
    """
    Text widget where timestamp portions are marked as non-editable.

    Design:
    - Insert timestamps and speaker labels with a specific tag.
    - Intercept key events such that edits inside those tagged regions
      are prevented.
    """

    TIMESTAMP_TAG = "timestamp"
    SPEAKER_TAG_PREFIX = "speaker_"

    def __init__(self, master: Optional[tk.Misc] = None, **kwargs) -> None:
        """
        Initialize the widget.

        :param master: Parent widget.
        :param kwargs: Forwarded to ScrolledText.
        """
        super().__init__(master, wrap="word", **kwargs)

        # Configure styling for the timestamp tag for visual distinction.
        self.tag_configure(self.TIMESTAMP_TAG, foreground="gray")

        # Bind to key events to protect timestamp regions.
        self.bind("<Key>", self._on_key)

    def _on_key(self, event: tk.Event) -> str:
        """
        Intercept key presses to prevent edits inside timestamp regions.

        :param event: Tkinter event for the key press.
        :return: "break" to cancel the key, or None to allow it.
        """
        # Determine the insertion index before the key is applied.
        index = self.index("insert")

        # If the current index is inside a timestamp tag, block editing.
        tags = self.tag_names(index)
        if self.TIMESTAMP_TAG in tags:
            # Returning "break" cancels the default behavior.
            return "break"

        # Otherwise, allow normal key handling.
        return None

    def insert_sentence(
        self,
        speaker_name: str,
        speaker_color: str,
        start_time: Optional[float],
        end_time: Optional[float],
        text: str,
    ) -> None:
        """
        Insert a sentence with timestamp and speaker color.

        :param speaker_name: Name of the speaker.
        :param speaker_color: Color associated with the speaker.
        :param start_time: Start time as UNIX timestamp (seconds since epoch).
        :param end_time: End time as UNIX timestamp (seconds since epoch).
        :param text: The recognized sentence text.
        """
        # We format the timestamp and prepend it to the line.
        timestamp_str = self._format_timestamp(start_time, end_time)
        line_prefix = f"[{timestamp_str}] {speaker_name}: "

        # Insert the timestamp and speaker label, tagging the timestamp.
        start_index = self.index("end-1c")
        self.insert("end", line_prefix)
        end_index = self.index("end-1c")
        self.tag_add(
            self.TIMESTAMP_TAG,
            start_index,
            f"{start_index} + {len(line_prefix)}c",
        )

        # Insert the sentence text and mark it with a speaker-specific tag.
        text_start = self.index("end-1c")
        self.insert("end", text + "\n")
        text_end = self.index("end-1c")

        speaker_tag = f"{self.SPEAKER_TAG_PREFIX}{speaker_name}"
        if speaker_tag not in self.tag_names():
            # Configure the speaker tag (foreground color) only once.
            self.tag_configure(speaker_tag, foreground=speaker_color)

        self.tag_add(speaker_tag, text_start, text_end)

        # Scroll to the end so the latest sentence is visible.
        self.see("end")

    def _format_timestamp(
        self,
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> str:
        """
        Format timestamps as a user-friendly string based on real-world time.

        :param start_time: Start time as UNIX timestamp (seconds).
        :param end_time: End time as UNIX timestamp (seconds).
        :return: Formatted "HH:MM:SS.mmm-HH:MM:SS.mmm" or "unknown".
        """
        if start_time is None or end_time is None:
            return "unknown"

        def fmt(t: float) -> str:
            # Convert UNIX timestamp to local datetime and format with millis.
            dt = datetime.fromtimestamp(t)
            return dt.strftime("%H:%M:%S.%f")[:-3]

        return f"{fmt(start_time)}-{fmt(end_time)}"

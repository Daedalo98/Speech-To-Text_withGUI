"""
Speaker manager panel.

Responsible for:
- Adding new speakers.
- Assigning unique colors.
- Allowing editing (name, color) via double-click.
- Exposing and changing the currently active speaker.
- Forwarding an "Export" button click to the main application.
"""

from __future__ import annotations

import itertools
import tkinter as tk
from tkinter import colorchooser, simpledialog, messagebox
from typing import Callable, Dict, Optional, List


class SpeakerManager(tk.Frame):
    """
    Panel managing speakers and their color-coded buttons.
    """

    def __init__(
        self,
        master: Optional[tk.Misc] = None,
        on_active_speaker_changed: Optional[Callable[[str, str], None]] = None,
        on_export_clicked: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the speaker manager.

        :param master: Parent widget.
        :param on_active_speaker_changed: Callback invoked when the user
                                          changes the active speaker.
                                          Signature: (speaker_name, color).
        :param on_export_clicked: Callback invoked when the Export button
                                  is clicked (no arguments).
        :param kwargs: Extra options for tk.Frame.
        """
        super().__init__(master, **kwargs)

        self._on_active_speaker_changed = on_active_speaker_changed
        self._on_export_clicked = on_export_clicked

        # Store speakers as a mapping from speaker name to (color, button).
        self._speakers: Dict[str, Dict[str, object]] = {}
        self._active_speaker: Optional[str] = None

        # Color palette iterator for initial colors (unique, reusable).
        self._color_cycle = itertools.cycle(
            [
                "#1f77b4",  # blue
                "#ff7f0e",  # orange
                "#2ca02c",  # green
                "#d62728",  # red
                "#9467bd",  # purple
                "#8c564b",  # brown
                "#e377c2",  # pink
                "#7f7f7f",  # gray
            ]
        )

        # Build UI controls.
        self._build_ui()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def active_speaker(self) -> Optional[str]:
        """
        Return the name of the currently active speaker (or None).
        """
        return self._active_speaker

    def get_speaker_color(self, speaker_name: str) -> str:
        """
        Get the color associated with a speaker (or black by default).

        :param speaker_name: The speaker's name.
        :return: Hex color string.
        """
        speaker = self._speakers.get(speaker_name)
        if speaker is None:
            return "#000000"
        return str(speaker["color"])

    def get_speakers(self) -> List[str]:
        """
        Return a list of speaker names in insertion order.
        """
        return list(self._speakers.keys())

    def get_all_speakers(self) -> List[Dict[str, str]]:
        """
        Return all speakers with their colors, as a list of dicts:
        { "name": ..., "color": ... }.
        """
        return [
            {"name": name, "color": str(data["color"])}
            for name, data in self._speakers.items()
        ]

    def set_active_speaker(self, name: str) -> None:
        """
        Public wrapper to set the active speaker by name.

        :param name: Speaker name to activate.
        """
        self._set_active_speaker(name)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """
        Build the speaker manager UI layout.
        """
        # Frame for control buttons (Start/Stop, Add Speaker, Export).
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill="x", pady=4)

        # Start/Stop button (actual behavior attached by the main app).
        self.start_stop_button = tk.Button(
            controls_frame,
            text="Start",
            command=self._on_start_stop_clicked,
        )
        self.start_stop_button.pack(side="left", padx=2)

        # Add Speaker button.
        self.add_speaker_button = tk.Button(
            controls_frame,
            text="Add Speaker",
            command=self._on_add_speaker_clicked,
        )
        self.add_speaker_button.pack(side="left", padx=2)

        # Export button: forwards to the main application callback.
        self.export_button = tk.Button(
            controls_frame,
            text="Export",
            command=self._on_export_button_clicked,
        )
        self.export_button.pack(side="left", padx=2)

        # Frame for speaker buttons.
        self.speakers_frame = tk.Frame(self)
        self.speakers_frame.pack(fill="both", expand=True, pady=4)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _on_start_stop_clicked(self) -> None:
        """
        Handle the Start/Stop button click.

        The main application overrides this button's command to connect it
        to the transcription start/stop logic. This method remains as a
        placeholder for possible local behavior.
        """
        pass

    def _on_export_button_clicked(self) -> None:
        """
        Forward the Export button click to the callback provided
        by the main application.
        """
        if self._on_export_clicked is not None:
            self._on_export_clicked()

    def _on_add_speaker_clicked(self) -> None:
        """
        Ask the user for a new speaker's name and assign a unique color.
        """
        name = simpledialog.askstring(
            "New Speaker", "Enter speaker name:", parent=self
        )
        if not name:
            return

        if name in self._speakers:
            messagebox.showerror(
                "Duplicate Speaker",
                f"A speaker named '{name}' already exists.",
                parent=self,
            )
            return

        color = next(self._color_cycle)
        self._add_speaker(name, color)

    def _on_add_speaker_clicked_with_name(self, name: str) -> None:
        """
        Add a new speaker with a provided name (programmatically).
        
        :param name: Speaker name to add.
        """
        if name in self._speakers:
            messagebox.showerror(
                "Duplicate Speaker",
                f"A speaker named '{name}' already exists.",
                parent=self,
            )
            return

        color = next(self._color_cycle)
        self._add_speaker(name, color)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _add_speaker(self, name: str, color: str) -> None:
        """
        Add a new speaker button.

        :param name: Speaker name.
        :param color: Hex color string.
        """
        button = tk.Button(
            self.speakers_frame,
            text=name,
            bg=color,
            activebackground=color,
            command=lambda n=name: self._set_active_speaker(n),
        )
        button.pack(fill="x", pady=2)

        # Bind double-click to edit speaker properties (name, color).
        button.bind("<Double-Button-1>", lambda event, n=name: self._edit_speaker(n))

        self._speakers[name] = {"color": color, "button": button}

        # NEW BEHAVIOR: the newly added speaker becomes the active one.
        self.set_active_speaker(name)

    def _set_active_speaker(self, name: str) -> None:
        """
        Mark a given speaker as active and update callbacks.

        :param name: Speaker name to activate.
        """
        if name not in self._speakers:
            return

        self._active_speaker = name
        color = self.get_speaker_color(name)

        # Give a visual hint (relief style) to indicate the active speaker.
        for s_name, data in self._speakers.items():
            button = data["button"]
            if s_name == name:
                button.configure(relief="sunken")
            else:
                button.configure(relief="raised")

        # Notify the app if a callback is provided.
        if self._on_active_speaker_changed is not None:
            self._on_active_speaker_changed(name, color)

    def _edit_speaker(self, old_name: str) -> None:
        """
        Allow editing of a speaker's name and color via dialogs.

        :param old_name: Current speaker name.
        """
        data = self._speakers.get(old_name)
        if data is None:
            return

        button: tk.Button = data["button"]  # type: ignore[assignment]
        current_color = str(data["color"])

        # Ask for a new name (pre-fill with old name).
        new_name = simpledialog.askstring(
            "Edit Speaker",
            "Edit speaker name:",
            initialvalue=old_name,
            parent=self,
        )
        if not new_name:
            new_name = old_name

        # Ask for a new color; fallback to current if user cancels.
        color_tuple = colorchooser.askcolor(
            title="Choose speaker color", initialcolor=current_color
        )
        new_color = color_tuple[1] or current_color

        # Update button text and color.
        button.configure(text=new_name, bg=new_color, activebackground=new_color)

        # Remove old entry and add new one.
        del self._speakers[old_name]
        self._speakers[new_name] = {"color": new_color, "button": button}

        # Update active speaker name if needed.
        if self._active_speaker == old_name:
            self._active_speaker = new_name

        # Notify about active speaker change to propagate color/name.
        if self._on_active_speaker_changed is not None:
            self._on_active_speaker_changed(new_name, new_color)

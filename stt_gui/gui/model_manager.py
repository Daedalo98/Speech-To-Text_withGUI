"""
Model manager panel for selecting Vosk models.

Responsible for:
- Listing available Vosk models from the models directory.
- Allowing the user to select which model to use.
- Providing the selected model path to the main application.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from pathlib import Path

from stt_gui.config.settings import DEFAULT_MODELS_DIR, list_available_vosk_models


class ModelManager(tk.Frame):
    """
    Panel managing Vosk model selection.
    """

    def __init__(
        self,
        master: Optional[tk.Misc] = None,
        on_model_selected: Optional[Callable[[Path], None]] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the model manager.

        :param master: Parent widget.
        :param on_model_selected: Callback invoked when the user
                                  selects a different model.
                                  Signature: (model_path: Path).
        :param kwargs: Extra options for tk.Frame.
        """
        super().__init__(master, **kwargs)

        self._on_model_selected = on_model_selected
        self._current_model: Optional[Path] = None

        # Get available models
        self._available_models = list_available_vosk_models(DEFAULT_MODELS_DIR)

        # Build UI controls.
        self._build_ui()

        # Select the first model by default
        if self._available_models:
            self._select_model(self._available_models[0])

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def current_model(self) -> Optional[Path]:
        """
        Return the currently selected model path (or None).
        """
        return self._current_model

    def get_model_display_name(self, model_path: Path) -> str:
        """
        Get a user-friendly name for a model path.

        :param model_path: Path to the model directory.
        :return: Display name (just the directory name).
        """
        return model_path.name

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """
        Build the model manager UI layout.
        """
        # Frame for label and dropdown
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill="x", padx=4, pady=4)

        # Label
        label = tk.Label(controls_frame, text="Vosk Model:", anchor="w")
        label.pack(side="left", padx=2)

        # Dropdown (combobox) for model selection
        self.model_var = tk.StringVar()
        
        # Create list of display names
        model_names = [self.get_model_display_name(m) for m in self._available_models]

        self.model_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.model_var,
            values=model_names,
            state="readonly",
            width=40,
        )
        self.model_combo.pack(side="left", padx=2, fill="x", expand=True)
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_combo_selected)

        # Refresh button
        refresh_button = tk.Button(
            controls_frame,
            text="Refresh Models",
            command=self._on_refresh_clicked,
        )
        refresh_button.pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _on_model_combo_selected(self, event=None) -> None:
        """
        Handle model selection from the combobox.
        """
        selected_name = self.model_var.get()
        
        # Find the model path by name
        for model_path in self._available_models:
            if self.get_model_display_name(model_path) == selected_name:
                self._select_model(model_path)
                return

    def _on_refresh_clicked(self) -> None:
        """
        Refresh the list of available models.
        """
        self._available_models = list_available_vosk_models(DEFAULT_MODELS_DIR)

        if not self._available_models:
            messagebox.showwarning(
                "No Models Found",
                f"No Vosk models found in:\n{DEFAULT_MODELS_DIR}",
                parent=self,
            )
            return

        # Update the combobox values
        model_names = [self.get_model_display_name(m) for m in self._available_models]
        self.model_combo["values"] = model_names

        # Select the first model
        self._select_model(self._available_models[0])
        messagebox.showinfo(
            "Models Refreshed",
            f"Found {len(self._available_models)} model(s).",
            parent=self,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _select_model(self, model_path: Path) -> None:
        """
        Select a model and notify the callback.

        :param model_path: Path to the model directory.
        """
        if not model_path.exists():
            messagebox.showerror(
                "Model Not Found",
                f"Model directory does not exist:\n{model_path}",
                parent=self,
            )
            return

        self._current_model = model_path
        display_name = self.get_model_display_name(model_path)
        self.model_var.set(display_name)

        # Notify the app if a callback is provided.
        if self._on_model_selected is not None:
            self._on_model_selected(model_path)

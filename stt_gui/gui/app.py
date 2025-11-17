"""
Main application frame that combines all GUI components and
coordinates audio and STT threads.

High-level responsibilities:
- Create and arrange the three main sections:
  A. Speaker manager + Start/Stop + Export.
  B. Live and finalized transcription.
  C. Notes / annotations panel.
- Start/stop audio capture and Vosk engine.
- Show a "wait, starting..." message while Vosk initializes.
- Use real-world timestamps (wall-clock) for segments.
- Export speakers, transcript, and notes to JSON.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from stt_gui.config import settings
from stt_gui.stt.vosk_engine import VoskEngine, STTResult


from ..audio.audio_stream import AudioStream
from ..config.settings import (
    DEFAULT_VOSK_MODEL_PATH,
    GUI_POLL_INTERVAL_MS,
)
from ..stt.vosk_engine import STTResult, VoskEngine
from .model_manager import ModelManager
from .notes_panel import NotesPanel
from .speaker_manager import SpeakerManager
from .transcription_panel import TranscriptionPanel


class SpeechToTextApp(tk.Frame):
    """
    Main application GUI frame that embeds all panels.
    """
    def __init__(self, master=None, **kwargs) -> None:
        """
        Initialize the application frame.

        :param master: Parent Tk widget (typically the root window).
        :param kwargs: Extra options forwarded to tk.Frame.
        """
        super().__init__(master, **kwargs)

        # Model path selected by user (updated by ModelManager callback).
        self._model_path: Optional[Path] = DEFAULT_VOSK_MODEL_PATH

        # Audio and STT engine instances (created lazily on start).
        self._audio_stream: Optional[AudioStream] = None
        self._vosk_engine: Optional[VoskEngine] = None

        # Queues for audio and results, shared with VoskEngine
        self._audio_queue: "queue.Queue[bytes]" = queue.Queue()
        self._result_queue: "queue.Queue[STTResult]" = queue.Queue()

        # Engine starts as None, only created after a model is selected
        self._engine: Optional[VoskEngine] = None

        # State flag to know if we are currently recording.
        self._is_running = False

        # Wall-clock time (UNIX seconds) when the audio stream starts.
        # Used to convert Vosk-relative timestamps into real-world time.
        self._stream_start_wall_time: Optional[float] = None

        # Build all GUI components.
        self._build_ui()

        # Schedule periodic polling of STT results.
        self.after(GUI_POLL_INTERVAL_MS, self._poll_stt_results)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """
        Build the three main sections of the application.
        """
        # Use a horizontal layout:
        #   [left: model selector + speaker manager + transcription]
        #   [right: notes panel]
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = tk.Frame(self)
        right_frame.pack(side="right", fill="both", expand=False)

        # Top: model manager (for selecting Vosk model).
        self.model_manager = ModelManager(
            left_frame,
            on_model_selected=self._on_model_selected,
        )
        self.model_manager.pack(fill="x", padx=4, pady=4)

        # Upper-middle: speaker manager (with Start/Stop and Export).
        self.speaker_manager = SpeakerManager(
            left_frame,
            on_active_speaker_changed=self._on_active_speaker_changed,
            on_export_clicked=self._on_export_clicked,
        )
        self.speaker_manager.pack(fill="x", padx=4, pady=4)

        # We attach the start/stop behavior at app level to keep the
        # speaker manager reusable.
        self.speaker_manager.start_stop_button.config(
            command=self._on_start_stop_clicked
        )

        # Middle: transcription panel.
        self.transcription_panel = TranscriptionPanel(
            left_frame, on_note_created=self._on_note_created
        )
        self.transcription_panel.pack(fill="both", expand=True, padx=4, pady=4)

        # Right: notes panel.
        notes_label = tk.Label(right_frame, text="Notes", anchor="w")
        notes_label.pack(fill="x", padx=4, pady=(4, 0))

        self.notes_panel = NotesPanel(right_frame)
        self.notes_panel.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------------
    # Speaker & note callbacks
    # ------------------------------------------------------------------
    def _on_model_selected(self, model_path: Path) -> None:
        """
        Callback from ModelManager when the user selects a model.

        :param model_path: Path to the selected model directory.
        """
        self._model_path = model_path

    def _on_active_speaker_changed(self, name: str, color: str) -> None:
        """
        Callback from SpeakerManager when active speaker changes.

        :param name: New active speaker name.
        :param color: New active speaker color.
        """
        self.transcription_panel.update_active_speaker(name, color)

    def _on_note_created(
        self,
        speaker_name: str,
        speaker_color: str,
        timestamp_str: str,
    ) -> None:
        """
        Callback from TranscriptionPanel when the user requests a note.

        Here we create an empty note (placeholder), which the user
        can edit directly in the notes panel.
        """
        placeholder_text = "(edit this note...)"
        self.notes_panel.add_note(
            speaker_name=speaker_name,
            speaker_color=speaker_color,
            timestamp_str=timestamp_str,
            text=placeholder_text,
        )

    # ------------------------------------------------------------------
    # Start/Stop logic
    # ------------------------------------------------------------------
    def _on_start_stop_clicked(self) -> None:
        """
        Handle Start/Stop button click.

        - If not running, start audio + Vosk in a background thread,
          showing "Wait, starting..." in the live panel.
        - If running, stop them and clean up.
        """
        if not self._is_running:
            self._start_transcription()
        else:
            self._stop_transcription()

    def _start_transcription(self) -> None:
        """
        Start audio capture and STT processing, asynchronously.

        - Ensure at least one speaker exists.
        - Ensure the first speaker is active by default.
        - Show "Wait, starting..." while Vosk model loads.
        """
        # Ensure at least one speaker is defined.
        speakers = self.speaker_manager.get_speakers()
        if not speakers:
            messagebox.showwarning(
                "No speakers",
                "Please add at least one speaker before starting transcription.",
                parent=self,
            )
            return

        # NEW BEHAVIOR: when starting, set by default the first speaker,
        # if none is currently active.
        if self.speaker_manager.active_speaker is None:
            first = speakers[0]
            self.speaker_manager.set_active_speaker(first)

        # Check that the Vosk model path exists.
        if not self._model_path or not self._model_path.exists():
            messagebox.showerror(
                "Vosk Model Missing",
                f"Vosk model not found at:\n{self._model_path}\n\n"
                "Please select a valid model from the model dropdown.",
                parent=self,
            )
            return

        # Inform the user that we are starting up (model loading may take a bit).
        self.transcription_panel.update_live_partial(
            text="Wait, starting...",
            start_time=None,
            end_time=None,
        )
        self.speaker_manager.start_stop_button.config(text="Starting...")

        def init_worker() -> None:
            """
            Background initialization to avoid blocking the GUI.

            - Create AudioStream and VoskEngine if needed.
            - Start them.
            - Record the wall-clock start time for timestamps.
            """
            try:
                # Create audio stream if not done yet.
                if self._audio_stream is None:
                    self._audio_stream = AudioStream(self._audio_queue)

                # Create Vosk engine if not done yet.
                if self._vosk_engine is None:
                    self._vosk_engine = VoskEngine(
                        model_path=self._model_path,
                        audio_queue=self._audio_queue,
                        result_queue=self._result_queue,
                    )

                # Record the wall-clock time at which the stream starts.
                self._stream_start_wall_time = time.time()

                # Start audio capture and STT engine.
                self._audio_stream.start()
                self._vosk_engine.start()

                self._is_running = True

                # Switch back to the main thread to update the GUI.
                def on_ready() -> None:
                    self.transcription_panel.update_live_partial(
                        text="",
                        start_time=None,
                        end_time=None,
                    )
                    self.speaker_manager.start_stop_button.config(text="Stop")

                self.after(0, on_ready)

            except Exception as exc:  # noqa: BLE001
                # If something fails, reset state and report the error.
                self._is_running = False
                self._stream_start_wall_time = None

                def on_error() -> None:
                    self.transcription_panel.update_live_partial(
                        text="",
                        start_time=None,
                        end_time=None,
                    )
                    self.speaker_manager.start_stop_button.config(text="Start")
                    messagebox.showerror(
                        "Error starting transcription", str(exc), parent=self
                    )

                self.after(0, on_error)

        # Launch initialization in a background thread.
        threading.Thread(target=init_worker, daemon=True).start()

    def _stop_transcription(self) -> None:
        """
        Stop audio capture and STT processing.
        """
        if self._audio_stream is not None:
            self._audio_stream.stop()
        if self._vosk_engine is not None:
            self._vosk_engine.stop()

        self._is_running = False
        self._stream_start_wall_time = None
        self.speaker_manager.start_stop_button.config(text="Start")

    # ------------------------------------------------------------------
    # Export to JSON
    # ------------------------------------------------------------------
    def _on_export_clicked(self) -> None:
        """
        Handle Export button click.

        Gathers speakers, transcription lines, and notes, then exports
        them to a JSON file selected by the user.
        """
        # Build the data structure.
        data = self._build_export_data()

        # Ask the user for a destination file.
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export transcription and notes",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        # Write JSON file.
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Export successful",
                f"Transcription and notes exported to:\n{file_path}",
                parent=self,
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Export failed",
                f"Could not export data:\n{exc}",
                parent=self,
            )

    def _build_export_data(self) -> dict:
        """
        Build a JSON-serializable object representing the session.

        Structure:
        {
          "metadata": {...},
          "speakers": [...],
          "transcript": [...],
          "notes": [...]
        }
        """
        # Speakers: from SpeakerManager.
        speakers = self.speaker_manager.get_all_speakers()

        # Transcript sentences: from TranscriptionPanel.
        transcript = self.transcription_panel.get_sentences()

        # Notes: from NotesPanel.
        notes = self.notes_panel.get_notes()

        metadata = {
            "exported_at": datetime.now().isoformat(timespec="milliseconds"),
        }

        return {
            "metadata": metadata,
            "speakers": speakers,
            "transcript": transcript,
            "notes": notes,
        }

    # ------------------------------------------------------------------
    # STT result polling
    # ------------------------------------------------------------------
    def _poll_stt_results(self) -> None:
        """
        Periodically poll the STT result queue and update the GUI.

        This method is scheduled using Tk's `after` mechanism so that
        all GUI updates occur on the main thread.
        """
        try:
            while True:
                # Non-blocking get; break when queue is empty.
                result = self._result_queue.get_nowait()
                self._handle_stt_result(result)
        except queue.Empty:
            pass

        # Re-schedule this method.
        self.after(GUI_POLL_INTERVAL_MS, self._poll_stt_results)

    def _handle_stt_result(self, result: STTResult) -> None:
        """
        Update the GUI based on a new STTResult.

        :param result: STTResult from the STT engine.
        """
        # Real-world times are computed based on the stream start time
        # and the relative times provided by Vosk.
        real_start: Optional[float] = None
        real_end: Optional[float] = None

        if (
            self._stream_start_wall_time is not None
            and result.start_time is not None
            and result.end_time is not None
        ):
            real_start = self._stream_start_wall_time + result.start_time
            real_end = self._stream_start_wall_time + result.end_time

        if result.type == "partial":
            # Partial results: show text in the live area (without timestamp).
            self.transcription_panel.update_live_partial(
                text=result.text,
                start_time=None,
                end_time=None,
            )
        elif result.type == "final":
            # Final result: insert a new sentence with real-world times.
            self.transcription_panel.add_final_sentence(
                text=result.text,
                start_time=real_start,
                end_time=real_end,
            )

            # Clear the live label when a final segment is added.
            self.transcription_panel.update_live_partial(
                text="",
                start_time=None,
                end_time=None,
            )

    # ------------------------------------------------------------------
    # Widget teardown
    # ------------------------------------------------------------------
    def destroy(self) -> None:
        """
        Override destroy to ensure threads are stopped.

        This is called when the Tk window is closed.
        """
        self._stop_transcription()
        super().destroy()

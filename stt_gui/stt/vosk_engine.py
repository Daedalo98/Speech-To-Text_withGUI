"""
VoskEngine: processes audio chunks using Vosk and outputs STTResult objects.

IMPORTANT:
- This version never references the GUI.
- It outputs relative start/end times (Vosk time offsets).
- GUI converts offsets to real-world timestamps.
"""

from __future__ import annotations

import json
import threading
import queue
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vosk import Model, KaldiRecognizer

@dataclass
class STTResult:
    """
    Represents a speech recognition result.

    type:
        - "partial" for partial results
        - "final"   for completed segments
    text:
        - recognized text
    start_time, end_time:
        - relative times from Vosk (NOT wall clock times)
    """
    type: str
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class VoskEngine:
    """
    Runs a Vosk KaldiRecognizer in a background thread.

    Audio bytes are read from audio_queue.
    Recognition results are pushed into result_queue.
    """

    def __init__(
        self,
        model_path: Path,
        audio_queue: "queue.Queue[bytes]",
        result_queue: "queue.Queue[STTResult]",
    ) -> None:
        self._model_path = model_path
        self._audio_queue = audio_queue
        self._result_queue = result_queue

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Load model
        self._model = Model(str(self._model_path))
        self._recognizer = KaldiRecognizer(self._model, 16000)
        self._recognizer.SetWords(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        """
        Continuously read audio chunks and process them with Vosk.
        """
        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._recognizer.AcceptWaveform(chunk):
                raw = json.loads(self._recognizer.Result())
                self._handle_final_result(raw)
            else:
                raw = json.loads(self._recognizer.PartialResult())
                self._handle_partial_result(raw)

        # Emit final result when stopping
        try:
            raw = json.loads(self._recognizer.FinalResult())
            self._handle_final_result(raw)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Result handlers
    # ------------------------------------------------------------------
    def _handle_partial_result(self, raw: dict) -> None:
        """
        Handle a partial Vosk result.
        """
        text = raw.get("partial", "").strip()
        if not text:
            return

        self._result_queue.put(
            STTResult(
                type="partial",
                text=text,
                start_time=None,
                end_time=None,
            )
        )

    def _handle_final_result(self, raw: dict) -> None:
        """
        Handle a final Vosk result.
        Extract start/end offsets from 'result' list.
        """
        text = raw.get("text", "").strip()
        if not text:
            return

        words = raw.get("result", [])
        if words:
            start_time = float(words[0].get("start", 0.0))
            end_time = float(words[-1].get("end", 0.0))
        else:
            start_time = None
            end_time = None

        # No GUI reference here — GUI handles conversion to wall time
        self._result_queue.put(
            STTResult(
                type="final",
                text=text,
                start_time=start_time,
                end_time=end_time,
            )
        )

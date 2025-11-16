"""
Audio streaming utilities based on the `sounddevice` library.

This module provides a small abstraction over sounddevice's InputStream,
pushing raw audio frames into a thread-safe queue that the STT engine
can consume.
"""

from __future__ import annotations

import queue
import threading
from typing import Optional, Callable

import sounddevice as sd

from ..config.settings import SAMPLE_RATE, CHANNELS, BLOCK_SIZE


class AudioStream:
    """
    Handle low-level audio capture and push frames into a queue.

    The core idea:
    - We create a `sounddevice.InputStream` with a callback.
    - In the callback, we convert the NumPy audio buffer to bytes and
      put it into a queue.
    - The STT engine then pulls from that queue.
    """

    def __init__(
        self,
        audio_queue: "queue.Queue[bytes]",
        on_error: Optional[Callable[[Exception], None]] = None) -> None:
        """
        Initialize an AudioStream.

        :param audio_queue: Queue into which raw audio frames (bytes) are put.
        :param on_error: Optional callback invoked if the internal stream
                         raises an exception.
        """
        self._audio_queue = audio_queue
        self._on_error = on_error

        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._is_running = False

    def _callback(self, indata, frames, time, status) -> None:
        """
        Callback invoked by sounddevice for each audio block.

        :param indata: NumPy array containing captured audio samples.
        :param frames: Number of frames (samples per channel).
        :param time: Low-level timing info (not used here).
        :param status: Status of the audio stream (e.g., underflow).
        """
        # If there's an error status, we could log or handle it.
        if status:
            # Here we simply print; in a real app you might use logging.
            print(f"Audio stream status: {status}")

        # Convert the audio buffer to raw bytes.
        try:
            data_bytes = indata.tobytes()
            # Non-blocking put to avoid blocking the callback; if the queue
            # is full, we drop the frame (simple back-pressure).
            self._audio_queue.put_nowait(data_bytes)
        except Exception as exc:  # noqa: BLE001
            # If anything goes wrong in callback, we forward to the error
            # handler if provided.
            if self._on_error is not None:
                self._on_error(exc)

    def start(self) -> None:
        """
        Start the audio input stream.

        Creates and starts a `sounddevice.InputStream` if not already running.
        """
        with self._lock:
            if self._is_running:
                return

            # Create the InputStream with our callback.
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                callback=self._callback,
            )
            self._stream.start()
            self._is_running = True

    def stop(self) -> None:
        """
        Stop the audio input stream and release resources.
        """
        with self._lock:
            if not self._is_running:
                return

            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._is_running = False

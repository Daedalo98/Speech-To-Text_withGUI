"""
Central configuration values for the application.

This keeps magic numbers and paths in a single place, making them
easy to adjust or override later.
"""

from __future__ import annotations

from pathlib import Path

# Base directory of the project (three levels up from this file).
BASE_DIR = Path(__file__).resolve().parents[2]

# Default location of the Vosk model.
# You should download a Vosk model and point this to that directory.
# For example: models/vosk-model-small-en-us-0.15
DEFAULT_VOSK_MODEL_PATH = BASE_DIR / "models" / "vosk-model-it-0.22"

# Audio settings.
SAMPLE_RATE = 16000  # Vosk typically expects 16kHz audio.
CHANNELS = 1         # Mono audio is sufficient for STT.
BLOCK_SIZE = 8000    # Number of frames per block (tune for latency vs. CPU).

# Sentence segmentation settings.
# Currently, Vosk final results already respect pauses, but this can be used
# for additional logic (e.g., visual separation).
SENTENCE_PAUSE_THRESHOLD_SEC = 1.2

# GUI timing.
# How often (in milliseconds) the GUI checks for new STT results.
GUI_POLL_INTERVAL_MS = 100

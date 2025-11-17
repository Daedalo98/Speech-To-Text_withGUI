"""
Central configuration values for the application.

This keeps magic numbers and paths in a single place, making them
easy to adjust or override later.
"""

from __future__ import annotations

from pathlib import Path

# Base directory of the project (three levels up from this file).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Root directory where all Vosk models live
DEFAULT_MODELS_DIR = BASE_DIR / "models"

# Default Vosk model path (will be overridden by user selection)
DEFAULT_VOSK_MODEL_PATH = DEFAULT_MODELS_DIR / "vosk-model-en-us-0.22"

# Audio settings.
SAMPLE_RATE = 16000  # Vosk typically expects 16kHz audio.
CHANNELS = 1         # Mono audio is sufficient for STT.
BLOCK_SIZE = 8000    # Number of frames per block (tune for latency vs. CPU).

# Sentence segmentation settings.
# Currently, Vosk final results already respect pauses, but this can be used
# for additional logic (e.g., visual separation).
SENTENCE_PAUSE_THRESHOLD_SEC = 1.0  # Seconds of silence to consider end of sentence.

# GUI timing.
# How often (in milliseconds) the GUI checks for new STT results.
GUI_POLL_INTERVAL_MS = 100

def list_available_vosk_models(models_dir: Path | None = None) -> list[Path]:
    """
    Return a list of subdirectories under models_dir that look like Vosk models.
    """
    if models_dir is None:
        models_dir = DEFAULT_MODELS_DIR

    if not models_dir.exists():
        return []

    candidates = []
    for entry in models_dir.iterdir():
        if entry.is_dir():
            # Very simple heuristic: any non-empty dir is considered a model.
            # You can make this stricter by checking for 'model', 'am', 'graph', etc.
            try:
                next(entry.iterdir())
                candidates.append(entry)
            except StopIteration:
                # empty dir -> skip
                pass
    return candidates

"""
Sentence segmentation utilities.

While Vosk already finalizes segments based on pauses, this module
provides a simple abstraction for pause-based segmentation logic
and supports unit tests to validate the behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WordTiming:
    """
    Simple structure representing a word with start and end times.

    Times are in seconds, relative to some reference point (e.g., start
    of the stream or start of the recognition segment).
    """

    word: str
    start: float
    end: float


class SentenceSegmenter:
    """
    Basic pause-based sentence segmentation.

    The main rule is:
    - If the silence (gap) between two words exceeds a threshold, we
      consider this a potential sentence boundary.
    """

    def __init__(self, pause_threshold_sec: float) -> None:
        """
        Initialize the segmenter.

        :param pause_threshold_sec: Minimum gap between word end and the
                                    next word start to count as a boundary.
        """
        self.pause_threshold_sec = pause_threshold_sec

    def is_boundary(self, prev_end: float, next_start: float) -> bool:
        """
        Check whether the gap between prev_end and next_start is a boundary.

        :param prev_end: End time of previous word (in seconds).
        :param next_start: Start time of next word (in seconds).
        :return: True if the gap is >= pause_threshold_sec, else False.
        """
        gap = next_start - prev_end
        return gap >= self.pause_threshold_sec

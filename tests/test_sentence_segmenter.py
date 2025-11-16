"""
Simple unit tests for the SentenceSegmenter.

This test ensures that the basic gap-based boundary logic works
as expected.
"""

from __future__ import annotations

from stt_gui.stt.sentence_segmenter import SentenceSegmenter


def test_sentence_segmenter_boundary() -> None:
    """
    Verify that is_boundary responds correctly to gaps.
    """
    segmenter = SentenceSegmenter(pause_threshold_sec=1.0)

    # Gap smaller than threshold -> not a boundary.
    assert not segmenter.is_boundary(prev_end=1.0, next_start=1.5)

    # Gap larger than threshold -> boundary.
    assert segmenter.is_boundary(prev_end=1.0, next_start=2.5)

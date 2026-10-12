"""Tests for voice-call media helpers.

av/numpy ship with ADK as core dependencies; the importorskip guards below trip only on a
broken/partial native install.

Copyright PolyAI Limited
"""

import unittest

import pytest

pytest.importorskip("av")
pytest.importorskip("numpy")

import numpy as np  # noqa: E402  (import after importorskip guard)

from poly.call.media import (  # noqa: E402
    BLOCK_SAMPLES,
    SAMPLE_RATE,
    pcm_block_to_frame,
)


class PcmBlockToFrameTest(unittest.TestCase):
    """Tests for pcm_block_to_frame — the capture-block → AudioFrame path."""

    def test_round_trips_shape_and_samples(self):
        block = (np.random.rand(BLOCK_SAMPLES, 1) * 500).astype(np.int16)

        frame = pcm_block_to_frame(block, 0)

        self.assertEqual(frame.samples, BLOCK_SAMPLES)
        self.assertEqual(frame.sample_rate, SAMPLE_RATE)
        round_tripped = frame.to_ndarray()
        self.assertEqual(round_tripped.shape, (1, BLOCK_SAMPLES))
        self.assertEqual(round_tripped.dtype, np.int16)
        np.testing.assert_array_equal(round_tripped, block.reshape(1, -1))

    def test_pts_is_the_supplied_value(self):
        block = np.zeros((BLOCK_SAMPLES, 1), dtype=np.int16)

        self.assertEqual(pcm_block_to_frame(block, 0).pts, 0)
        self.assertEqual(pcm_block_to_frame(block, BLOCK_SAMPLES).pts, BLOCK_SAMPLES)


if __name__ == "__main__":
    unittest.main()

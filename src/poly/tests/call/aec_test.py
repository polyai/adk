"""Tests for voice-call acoustic echo cancellation.

The FarEndReference tests need only numpy; the EchoCanceller tests are skipped unless
the optional ``aec`` extra (pywebrtc-audio) is installed.

Copyright PolyAI Limited
"""

import unittest

import pytest

pytest.importorskip("numpy")

import numpy as np  # noqa: E402

from poly.call.aec import FarEndReference  # noqa: E402


class FarEndReferenceTest(unittest.TestCase):
    """Tests for the thread-safe far-end reference FIFO."""

    def test_read_returns_written_samples_in_order(self):
        ref = FarEndReference(max_samples=1000)
        ref.write(np.arange(10, dtype=np.int16))

        first = ref.read(4)
        second = ref.read(6)

        np.testing.assert_array_equal(first, np.arange(4, dtype=np.int16))
        np.testing.assert_array_equal(second, np.arange(4, 10, dtype=np.int16))

    def test_read_zero_fills_when_drained(self):
        ref = FarEndReference(max_samples=1000)
        ref.write(np.array([5, 6], dtype=np.int16))

        out = ref.read(5)

        self.assertEqual(len(out), 5)
        self.assertEqual(out.dtype, np.int16)
        np.testing.assert_array_equal(out, np.array([5, 6, 0, 0, 0], dtype=np.int16))

    def test_read_on_empty_returns_silence(self):
        ref = FarEndReference(max_samples=1000)
        np.testing.assert_array_equal(ref.read(3), np.zeros(3, dtype=np.int16))

    def test_write_drops_oldest_beyond_cap(self):
        ref = FarEndReference(max_samples=4)
        ref.write(np.array([1, 2, 3], dtype=np.int16))
        ref.write(np.array([4, 5, 6], dtype=np.int16))  # total 6 > cap 4

        # Only the most recent 4 samples are retained.
        np.testing.assert_array_equal(ref.read(4), np.array([3, 4, 5, 6], dtype=np.int16))

    def test_write_accepts_2d_block(self):
        ref = FarEndReference(max_samples=1000)
        ref.write(np.array([[7], [8], [9]], dtype=np.int16))  # (samples, 1)
        np.testing.assert_array_equal(ref.read(3), np.array([7, 8, 9], dtype=np.int16))


class EchoCancellerTest(unittest.TestCase):
    """Tests for the WebRTC APM echo-canceller wrapper (needs pywebrtc-audio)."""

    def setUp(self):
        pytest.importorskip("pywebrtc_audio")
        from poly.call.aec import EchoCanceller

        self._ec = EchoCanceller()

    def test_cancels_pure_echo(self):
        # near is pure echo of far (no local speech) -> should be strongly attenuated
        # once the adaptive filter converges.
        rng = np.random.default_rng(0)
        far_full = (rng.standard_normal(48000) * 3000).astype(np.int16)
        near_full = (far_full.astype(np.float32) * 0.6).astype(np.int16)

        out = []
        for i in range(0, len(far_full) - 480, 480):
            out.append(self._ec.process(near_full[i : i + 480], far_full[i : i + 480]))
        out = np.concatenate(out)

        skip = 16000  # let the filter converge
        rms = lambda x: float(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)  # noqa: E731
        atten_db = 20 * np.log10(rms(near_full[skip : skip + len(out) - skip]) / rms(out[skip:]))
        self.assertGreater(atten_db, 15.0)

    def test_returns_same_length_int16(self):
        block = np.zeros(480, dtype=np.int16)
        out = self._ec.process(block, block)
        self.assertEqual(len(out), 480)
        self.assertEqual(np.asarray(out).dtype, np.int16)


if __name__ == "__main__":
    unittest.main()

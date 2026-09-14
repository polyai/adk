"""Echo cancellation for voice calls (``--echo-cancellation``, on by default).

Wraps the WebRTC AudioProcessing Module via ``pywebrtc-audio`` — the same AEC3 the
browser's ``getUserMedia({echoCancellation: true})`` uses — plus a thread-safe buffer
that carries the speaker's played audio (the far-end reference) to the mic capture path.
Imported only when echo cancellation is active.
"""

from __future__ import annotations

import threading

import numpy as np

# Shown if the WebRTC APM can't be loaded (a broken install — it ships with ADK).
_AEC_UNAVAILABLE_HINT = (
    "Echo cancellation is unavailable (WebRTC APM failed to load). Reinstall ADK with:\n"
    "    pip install --force-reinstall polyai-adk"
)


class EchoCanceller:
    """WebRTC APM echo canceller over mono int16 blocks at the capture rate."""

    def __init__(self) -> None:
        """Create the underlying WebRTC echo canceller.

        Raises:
            RuntimeError: If the WebRTC APM (pywebrtc-audio) can't be loaded.
        """
        try:
            import pywebrtc_audio
        except ImportError as exc:  # pragma: no cover - exercised via the CLI hint
            raise RuntimeError(_AEC_UNAVAILABLE_HINT) from exc
        self._ec = pywebrtc_audio.EchoCanceller()

    def process(self, near: np.ndarray, far: np.ndarray) -> np.ndarray:
        """Return ``near`` with the echo of ``far`` removed.

        Args:
            near: Mic capture block, int16, shape ``(samples,)`` or ``(samples, 1)``.
            far: The far-end (played) reference block, same length as ``near``.

        Returns:
            The echo-cancelled block as 1-D int16.
        """
        near_1d = np.ascontiguousarray(near.reshape(-1), dtype=np.int16)
        far_1d = np.ascontiguousarray(far.reshape(-1), dtype=np.int16)
        return np.asarray(self._ec.process(near_1d, far_1d), dtype=np.int16)


class FarEndReference:
    """Thread-safe FIFO of recently-played samples (the AEC far-end reference).

    Written by the speaker's PortAudio callback thread, read by the mic capture path.
    Bounded so it cannot grow without limit; yields silence when drained (which is
    correct — no playback means no echo to cancel).
    """

    def __init__(self, max_samples: int) -> None:
        """Create an empty reference buffer bounded to ``max_samples``."""
        self._buffer = np.zeros(0, dtype=np.int16)
        self._max_samples = max_samples
        self._lock = threading.Lock()

    def write(self, block: np.ndarray) -> None:
        """Append played samples, dropping the oldest beyond the cap."""
        samples = np.ascontiguousarray(block.reshape(-1), dtype=np.int16)
        with self._lock:
            combined = np.concatenate([self._buffer, samples])
            if len(combined) > self._max_samples:
                combined = combined[-self._max_samples :]
            self._buffer = combined

    def read(self, n: int) -> np.ndarray:
        """Pop the next ``n`` reference samples, zero-filling if fewer are buffered."""
        with self._lock:
            if len(self._buffer) >= n:
                out, self._buffer = self._buffer[:n], self._buffer[n:]
                return out
            out = np.zeros(n, dtype=np.int16)
            out[: len(self._buffer)] = self._buffer
            self._buffer = np.zeros(0, dtype=np.int16)
            return out

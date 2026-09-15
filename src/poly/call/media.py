"""Microphone capture and speaker playback for voice calls."""

from __future__ import annotations

import asyncio
import logging
import threading
from fractions import Fraction
from typing import TYPE_CHECKING

import av
import numpy as np
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

# sounddevice is imported lazily inside the stream-opening methods below: importing it
# loads the native PortAudio library, which isn't present in headless environments (CI).
# Keeping the import local means the pure helpers in this module stay importable there.
if TYPE_CHECKING:
    import sounddevice as sd

logger = logging.getLogger(__name__)

# Opus-native capture parameters.
# 20 ms at 48 kHz = 960 samples per block.
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SAMPLES = 960
_TIME_BASE = Fraction(1, SAMPLE_RATE)

# Bound queues to ~10 blocks (~200 ms).
# Beyond this we drop rather than buffer.
_MAX_QUEUED_BLOCKS = 10


def pcm_block_to_frame(block: np.ndarray, pts: int) -> av.AudioFrame:
    """Convert an int16 PCM capture block into an aiortc audio frame.

    Args:
        block: Capture block shaped ``(samples, channels)`` as sounddevice yields.
        pts: Presentation timestamp — a running sample counter (see ``recv``).

    Returns:
        A mono ``s16`` AudioFrame at ``SAMPLE_RATE`` with pts/time_base set.
    """
    # sounddevice gives (samples, channels); packed s16 mono wants (1, samples).
    mono = block.reshape(-1).astype(np.int16)
    frame = av.AudioFrame.from_ndarray(mono.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = SAMPLE_RATE
    frame.pts = pts
    frame.time_base = _TIME_BASE
    return frame


class MicrophoneTrack(MediaStreamTrack):
    """An aiortc audio track sourced from the local microphone.

    When ``echo_canceller`` and ``reference`` are provided, each captured block is run
    through the echo canceller against the far-end (played) reference before it is sent,
    removing the agent's own audio picked up by the mic.
    """

    kind = "audio"

    def __init__(self, echo_canceller=None, reference=None) -> None:
        """Open the input stream and start feeding capture blocks to the loop."""
        import sounddevice as sd

        super().__init__()
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(_MAX_QUEUED_BLOCKS)
        self._pts = 0
        self._echo_canceller = echo_canceller
        self._reference = reference
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCK_SAMPLES,
            callback=self._on_audio,
        )
        self._stream.start()

    def _on_audio(self, indata: np.ndarray, _frames: int, _time, status) -> None:
        """PortAudio-thread callback: hand a copy of the block to the loop."""
        if status:
            logger.debug("microphone input status: %s", status)
        # Must copy — sounddevice reuses the buffer after the callback returns.
        self._loop.call_soon_threadsafe(self._enqueue, indata.copy())

    def _enqueue(self, block: np.ndarray) -> None:
        """Loop-thread: enqueue a block, dropping the oldest if full."""
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(block)

    async def recv(self) -> av.AudioFrame:
        """Return the next captured frame (paced naturally by the mic)."""
        if self.readyState != "live":
            raise MediaStreamError
        block = await self._queue.get()
        if self._echo_canceller is not None and self._reference is not None:
            near = block.reshape(-1)
            far = self._reference.read(len(near))
            block = self._echo_canceller.process(near, far)
        frame = pcm_block_to_frame(block, self._pts)
        self._pts += frame.samples
        return frame

    def stop(self) -> None:
        """Stop capture and release the input stream."""
        super().stop()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class SpeakerPlayer:
    """Plays a received aiortc audio track through the local speaker.

    Incoming frames are resampled to a canonical mono/s16/48 kHz stream and
    accumulated in a buffer that the PortAudio output callback drains.
    """

    def __init__(self, reference=None) -> None:
        """Prepare the resampler, output buffer, and (idle) consumer task.

        When ``reference`` is provided, the samples actually sent to the speaker are
        recorded there as the AEC far-end reference.
        """
        self._resampler = av.audio.resampler.AudioResampler(
            format="s16", layout="mono", rate=SAMPLE_RATE
        )
        self._buffer = np.zeros(0, dtype=np.int16)
        self._lock = threading.Lock()
        self._reference = reference
        self._stream: sd.OutputStream | None = None
        self._task: asyncio.Task | None = None

    def start(self, track: MediaStreamTrack) -> None:
        """Begin draining ``track`` to the speaker."""
        import sounddevice as sd

        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCK_SAMPLES,
            callback=self._on_output,
        )
        self._stream.start()
        self._task = asyncio.ensure_future(self._drain(track))

    async def _drain(self, track: MediaStreamTrack) -> None:
        """Pull frames from the track, resample, and append to the buffer."""
        try:
            while True:
                frame = await track.recv()
                for resampled in self._resampler.resample(frame):
                    samples = resampled.to_ndarray().reshape(-1).astype(np.int16)
                    with self._lock:
                        # Cap the backlog (~200 ms) so playback stays near-live.
                        cap = _MAX_QUEUED_BLOCKS * BLOCK_SAMPLES
                        combined = np.concatenate([self._buffer, samples])
                        self._buffer = combined[-cap:] if len(combined) > cap else combined
        except MediaStreamError:
            pass

    def _on_output(self, outdata: np.ndarray, frames: int, _time, status) -> None:
        """PortAudio-thread callback: fill ``outdata`` from the buffer."""
        if status:
            logger.debug("speaker output status: %s", status)
        with self._lock:
            available = min(frames, len(self._buffer))
            outdata[:available, 0] = self._buffer[:available]
            self._buffer = self._buffer[available:]
        if available < frames:
            outdata[available:, 0] = 0  # underrun → silence
        # Record what actually went to the DAC as the AEC far-end reference —
        # the best-aligned copy of the audio the mic will pick up as echo.
        if self._reference is not None:
            self._reference.write(outdata[:, 0].copy())

    def stop(self) -> None:
        """Stop playback and release the output stream."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

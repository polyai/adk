"""Play an audio recording through the local speaker.

Copyright PolyAI Limited
"""

from __future__ import annotations

import io
import logging

import av
import numpy as np
import requests

from poly.call.media import CHANNELS, SAMPLE_RATE

logger = logging.getLogger(__name__)

# Voice samples are a few seconds long, so a slow download means something is wrong.
DOWNLOAD_TIMEOUT_SECONDS = 30


class PlaybackError(Exception):
    """A recording couldn't be downloaded, decoded or played."""


def decode_audio(data: bytes) -> np.ndarray:
    """Decode an encoded recording (mp3, wav, …) to mono 16-bit samples at SAMPLE_RATE.

    Args:
        data: The file's bytes.

    Returns:
        The samples, ready to hand to sounddevice.

    Raises:
        PlaybackError: If the data isn't audio PyAV can decode.
    """
    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    chunks: list[np.ndarray] = []
    try:
        with av.open(io.BytesIO(data)) as container:
            for frame in container.decode(audio=0):
                for resampled in resampler.resample(frame):
                    chunks.append(resampled.to_ndarray().reshape(-1))
            # Passing None flushes the samples the resampler is still holding.
            for resampled in resampler.resample(None):
                chunks.append(resampled.to_ndarray().reshape(-1))
    except (av.FFmpegError, IndexError, ValueError) as e:
        raise PlaybackError(f"The recording couldn't be decoded: {e}") from e
    if not chunks:
        raise PlaybackError("The recording has no audio.")
    return np.concatenate(chunks).astype(np.int16)


def download_audio(url: str) -> bytes:
    """Download a recording.

    Args:
        url: Where the recording is.

    Returns:
        The file's bytes.

    Raises:
        PlaybackError: If the download fails.
    """
    try:
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as e:
        raise PlaybackError(f"The recording couldn't be downloaded: {e}") from e
    return response.content


def play_samples(samples: np.ndarray) -> None:
    """Play samples through the default output device and wait until they finish.

    Ctrl+C stops playback early.

    Raises:
        PlaybackError: If there's no output device to play through.
    """
    # Imported here: importing sounddevice loads PortAudio, which headless machines lack.
    import sounddevice as sd

    try:
        sd.play(samples.reshape(-1, CHANNELS), SAMPLE_RATE)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()
    except sd.PortAudioError as e:
        raise PlaybackError(f"The recording couldn't be played: {e}") from e


def play_audio_url(url: str) -> None:
    """Download a recording, decode it and play it through the local speaker.

    Args:
        url: Where the recording is.

    Raises:
        PlaybackError: If any step fails.
    """
    play_samples(decode_audio(download_audio(url)))

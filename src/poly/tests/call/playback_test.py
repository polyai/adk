"""Tests for playing a recording through the speaker.

Copyright PolyAI Limited
"""

import io
import sys
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import requests

from poly.call.media import SAMPLE_RATE
from poly.call.playback import (
    DOWNLOAD_TIMEOUT_SECONDS,
    PlaybackError,
    decode_audio,
    download_audio,
    play_audio_url,
    play_samples,
)


def wav_bytes(seconds: float = 0.5, rate: int = 16000, channels: int = 2) -> bytes:
    """A WAV file of a quiet tone, at a rate and channel count unlike playback's."""
    frames = int(seconds * rate)
    tone = (np.sin(np.linspace(0, 440 * 2 * np.pi * seconds, frames)) * 1000).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(np.repeat(tone, channels).tobytes())
    return buffer.getvalue()


def fake_sounddevice() -> SimpleNamespace:
    """A stand-in for sounddevice, which needs PortAudio and a speaker."""

    class PortAudioError(Exception):
        pass

    return SimpleNamespace(
        play=MagicMock(), wait=MagicMock(), stop=MagicMock(), PortAudioError=PortAudioError
    )


class DecodeAudioTest(unittest.TestCase):
    """Tests for decode_audio, which turns a file into samples sounddevice can play."""

    def test_audio_is_resampled_to_mono_at_the_playback_rate(self):
        """Half a second of 16 kHz stereo comes out as half a second of 48 kHz mono."""
        samples = decode_audio(wav_bytes(seconds=0.5, rate=16000, channels=2))

        self.assertEqual(samples.dtype, np.int16)
        self.assertEqual(samples.ndim, 1)
        self.assertAlmostEqual(len(samples) / SAMPLE_RATE, 0.5, delta=0.02)

    def test_data_that_is_not_audio_raises_playback_error(self):
        """Bytes PyAV can't read raise PlaybackError rather than a PyAV error."""
        with self.assertRaises(PlaybackError):
            decode_audio(b"<html>not a recording</html>")


class DownloadAudioTest(unittest.TestCase):
    """Tests for download_audio."""

    def test_returns_the_response_body(self):
        """The recording's bytes are fetched with a timeout."""
        response = MagicMock(content=b"audio")
        with patch("poly.call.playback.requests.get", return_value=response) as get:
            self.assertEqual(download_audio("https://example.com/a.mp3"), b"audio")

        get.assert_called_once_with("https://example.com/a.mp3", timeout=DOWNLOAD_TIMEOUT_SECONDS)

    def test_http_error_raises_playback_error(self):
        """A 404 or similar becomes a PlaybackError."""
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        with patch("poly.call.playback.requests.get", return_value=response):
            with self.assertRaises(PlaybackError) as ctx:
                download_audio("https://example.com/missing.mp3")

        self.assertIn("couldn't be downloaded", str(ctx.exception))

    def test_connection_error_raises_playback_error(self):
        """No network becomes a PlaybackError."""
        with patch(
            "poly.call.playback.requests.get", side_effect=requests.ConnectionError("offline")
        ):
            with self.assertRaises(PlaybackError):
                download_audio("https://example.com/a.mp3")


class PlaySamplesTest(unittest.TestCase):
    """Tests for play_samples, with sounddevice replaced."""

    def setUp(self):
        self.sd = fake_sounddevice()
        patcher = patch.dict(sys.modules, {"sounddevice": self.sd})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_plays_at_the_playback_rate_and_waits(self):
        """Samples go to the default device as one mono column, and playback is awaited."""
        play_samples(np.zeros(10, dtype=np.int16))

        samples, rate = self.sd.play.call_args.args
        self.assertEqual(samples.shape, (10, 1))
        self.assertEqual(rate, SAMPLE_RATE)
        self.sd.wait.assert_called_once()

    def test_ctrl_c_stops_playback_quietly(self):
        """Ctrl+C while playing stops the sound without raising."""
        self.sd.wait.side_effect = KeyboardInterrupt

        play_samples(np.zeros(10, dtype=np.int16))

        self.sd.stop.assert_called_once()

    def test_missing_output_device_raises_playback_error(self):
        """A PortAudio failure, such as no speaker, becomes a PlaybackError."""
        self.sd.play.side_effect = self.sd.PortAudioError("no default output device")

        with self.assertRaises(PlaybackError):
            play_samples(np.zeros(10, dtype=np.int16))


class PlayAudioUrlTest(unittest.TestCase):
    """Tests for play_audio_url, which downloads, decodes and plays."""

    def test_downloaded_recording_is_played(self):
        """The recording at the URL is decoded and handed to sounddevice."""
        sd = fake_sounddevice()
        response = MagicMock(content=wav_bytes())
        with (
            patch.dict(sys.modules, {"sounddevice": sd}),
            patch("poly.call.playback.requests.get", return_value=response),
        ):
            play_audio_url("https://example.com/a.wav")

        sd.play.assert_called_once()
        self.assertGreater(len(sd.play.call_args.args[0]), 0)

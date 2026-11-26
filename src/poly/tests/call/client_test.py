"""Tests for the WebRTC call driver.

The audio devices and the bridge transport are mocked, so these run without a
microphone, a speaker or a network.

Copyright PolyAI Limited
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("aiortc")

from poly.call.bridge import BridgeError  # noqa: E402
from poly.call.client import CallError, run_call  # noqa: E402
from poly.call.session import CallSession  # noqa: E402


def _session() -> CallSession:
    return CallSession(
        variant_id="",
        auth_token="t",
        region="us-1",
    )


@patch("poly.call.client.SpeakerPlayer")
@patch("poly.call.client.MicrophoneTrack")
class RunCallTest(unittest.TestCase):
    """Tests for run_call."""

    @patch("poly.call.client.run_bridge_call", new_callable=AsyncMock)
    def test_places_the_call_with_the_microphone_and_speaker(
        self, mock_bridge, mock_mic, mock_speaker
    ):
        mock_bridge.return_value = "LOCAL-1"
        on_started = MagicMock()

        asyncio.run(run_call(_session(), "caller", on_started=on_started))

        args, kwargs = mock_bridge.call_args
        self.assertEqual(args, (_session(), "caller"))
        self.assertIs(kwargs["source"], mock_mic.return_value)
        self.assertEqual(kwargs["on_agent_track"], mock_speaker.return_value.start)
        self.assertIs(kwargs["on_started"], on_started)
        self.assertIsInstance(kwargs["stop"], asyncio.Event)

    @patch("poly.call.client.run_bridge_call", new_callable=AsyncMock)
    def test_releases_the_audio_devices_when_the_call_ends(
        self, mock_bridge, mock_mic, mock_speaker
    ):
        mock_bridge.return_value = "LOCAL-1"

        asyncio.run(run_call(_session(), "caller"))

        mock_mic.return_value.stop.assert_called_once()
        mock_speaker.return_value.stop.assert_called_once()

    @patch("poly.call.client.run_bridge_call", new_callable=AsyncMock)
    def test_a_failed_call_is_a_call_error_and_still_releases_the_devices(
        self, mock_bridge, mock_mic, mock_speaker
    ):
        mock_bridge.side_effect = BridgeError("Could not start the call (503)")

        with self.assertRaises(CallError) as ctx:
            asyncio.run(run_call(_session(), "caller"))

        self.assertIn("503", str(ctx.exception))
        mock_mic.return_value.stop.assert_called_once()
        mock_speaker.return_value.stop.assert_called_once()

    @patch("poly.call.client.run_bridge_call", new_callable=AsyncMock)
    def test_without_echo_cancellation_the_devices_get_no_reference(
        self, mock_bridge, mock_mic, mock_speaker
    ):
        mock_bridge.return_value = "LOCAL-1"

        asyncio.run(run_call(_session(), "caller", aec=False))

        mock_mic.assert_called_once_with(echo_canceller=None, reference=None)
        mock_speaker.assert_called_once_with(reference=None)

    @patch("poly.call.aec.FarEndReference")
    @patch("poly.call.aec.EchoCanceller")
    @patch("poly.call.client.run_bridge_call", new_callable=AsyncMock)
    def test_echo_cancellation_shares_one_reference_between_the_devices(
        self, mock_bridge, mock_canceller, mock_reference, mock_mic, mock_speaker
    ):
        mock_bridge.return_value = "LOCAL-1"

        asyncio.run(run_call(_session(), "caller", aec=True))

        mock_mic.assert_called_once_with(
            echo_canceller=mock_canceller.return_value, reference=mock_reference.return_value
        )
        mock_speaker.assert_called_once_with(reference=mock_reference.return_value)


if __name__ == "__main__":
    unittest.main()

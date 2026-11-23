"""Tests for the WebRTC bridge transport.

The HTTP boundary (``requests``) is mocked; the request and response shapes are the
bridge's own.

Copyright PolyAI Limited
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

pytest.importorskip("aiortc")

from poly.call import bridge  # noqa: E402
from poly.call.bridge import (  # noqa: E402
    BridgeError,
    build_provision_body,
    events_socket_url,
    ice_configuration,
    parse_provision_response,
    resolve_bridge_url,
    run_bridge_call,
)
from poly.call.session import CallSession  # noqa: E402

BRIDGE = "https://api.test.poly.ai/webrtc-bridge"


def make_session(**overrides) -> CallSession:
    fields = {
        "account_id": "acc-1",
        "project_id": "proj-1",
        "variant_id": "",
        "auth_token": "studio-token",
        "bridge_url": BRIDGE,
    }
    fields.update(overrides)
    return CallSession(**fields)


def provision_payload() -> dict:
    """A complete provisioning response."""
    return {
        "callId": "LOCAL-1",
        "creds": {
            "provider": "sfu",
            "connectUrl": "/api/v1/call/LOCAL-1/sdp",
            "token": "call-token",
            "iceServers": [{"urls": "stun:stun.example:3478"}],
            "extra": {
                "eventsUrl": "/api/v1/call/LOCAL-1/events",
                "pullUrl": "/api/v1/call/LOCAL-1/sdp/pull",
                "renegotiateUrl": "/api/v1/call/LOCAL-1/sdp/renegotiate",
            },
        },
    }


def response(status: int = 200, payload: dict | None = None) -> MagicMock:
    """A ``requests`` response with the given status and JSON body."""
    mock = MagicMock()
    mock.status_code = status
    mock.ok = 200 <= status < 300
    mock.content = b"{}" if payload is not None else b""
    if payload is None:
        mock.json.side_effect = ValueError("no body")
    else:
        mock.json.return_value = payload
    return mock


class ResolveBridgeUrlTest(unittest.TestCase):
    """Tests for resolve_bridge_url and events_socket_url."""

    def test_resolves_a_path_against_the_bridge(self):
        self.assertEqual(
            resolve_bridge_url("/api/v1/call/x/sdp", BRIDGE + "/"),
            BRIDGE + "/api/v1/call/x/sdp",
        )

    def test_refuses_anything_that_could_leave_the_bridge(self):
        for path in (
            "https://elsewhere.example/sdp",
            "//elsewhere.example/sdp",
            "api/v1/call",
            "/api/v1/call?token=x",
            "/api/v1/call#frag",
            "/@elsewhere.example",
        ):
            with self.assertRaises(BridgeError, msg=path):
                resolve_bridge_url(path, BRIDGE)

    def test_events_socket_uses_the_websocket_scheme(self):
        self.assertEqual(
            events_socket_url("/api/v1/call/x/events", BRIDGE),
            "wss://api.test.poly.ai/webrtc-bridge/api/v1/call/x/events",
        )
        self.assertEqual(
            events_socket_url("/events", "http://localhost:8080"), "ws://localhost:8080/events"
        )


class ProvisionBodyTest(unittest.TestCase):
    """Tests for build_provision_body."""

    def test_sends_only_the_mode_when_nothing_else_is_set(self):
        self.assertEqual(build_provision_body(make_session(), ""), {"mode": "voice-agent"})

    def test_includes_variant_and_caller(self):
        body = build_provision_body(make_session(variant_id="VARIANT-x"), "user@example.com")
        self.assertEqual(
            body, {"mode": "voice-agent", "variantId": "VARIANT-x", "caller": "user@example.com"}
        )


class ParseProvisionResponseTest(unittest.TestCase):
    """Tests for parse_provision_response."""

    def test_reads_credentials(self):
        creds = parse_provision_response(provision_payload())
        self.assertEqual(creds.call_id, "LOCAL-1")
        self.assertEqual(creds.token, "call-token")
        self.assertEqual(creds.connect_url, "/api/v1/call/LOCAL-1/sdp")
        self.assertEqual(creds.pull_url, "/api/v1/call/LOCAL-1/sdp/pull")
        self.assertEqual(creds.renegotiate_url, "/api/v1/call/LOCAL-1/sdp/renegotiate")
        self.assertEqual(creds.events_url, "/api/v1/call/LOCAL-1/events")
        self.assertEqual(creds.ice_servers, [{"urls": "stun:stun.example:3478"}])

    def test_names_the_missing_fields(self):
        payload = provision_payload()
        del payload["creds"]["extra"]["pullUrl"]
        del payload["callId"]
        with self.assertRaises(BridgeError) as ctx:
            parse_provision_response(payload)
        self.assertIn("callId", str(ctx.exception))
        self.assertIn("pullUrl", str(ctx.exception))


class IceConfigurationTest(unittest.TestCase):
    """Tests for ice_configuration."""

    def test_uses_the_servers_the_bridge_sent(self):
        config = ice_configuration(
            [{"urls": ["turn:turn.example:3478"], "username": "u", "credential": "c"}]
        )
        self.assertEqual(len(config.iceServers), 1)
        self.assertEqual(config.iceServers[0].urls, ["turn:turn.example:3478"])
        self.assertEqual(config.iceServers[0].username, "u")
        self.assertEqual(config.iceServers[0].credential, "c")

    def test_falls_back_to_a_stun_server(self):
        config = ice_configuration([])
        self.assertEqual(len(config.iceServers), 1)
        self.assertTrue(config.iceServers[0].urls.startswith("stun:"))


class ProvisionTest(unittest.TestCase):
    """Tests for the provisioning request."""

    @patch("poly.call.bridge.requests.post")
    def test_posts_the_studio_token_to_the_bridge(self, mock_post):
        mock_post.return_value = response(200, provision_payload())

        creds = bridge._provision(make_session(variant_id="VARIANT-x"), "user@example.com")

        self.assertEqual(creds.call_id, "LOCAL-1")
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], BRIDGE + "/api/v1/call")
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer studio-token"})
        self.assertEqual(kwargs["json"]["variantId"], "VARIANT-x")
        self.assertFalse(kwargs["allow_redirects"])

    @patch("poly.call.bridge.requests.post")
    def test_a_refusal_naming_another_call_path_says_the_agent_is_unsupported(self, mock_post):
        mock_post.return_value = response(409, {"error": "unsupported", "fallback": "other"})

        with self.assertRaises(BridgeError) as ctx:
            bridge._provision(make_session(), "")

        self.assertIn("can't be called from the ADK yet", str(ctx.exception))

    @patch("poly.call.bridge.requests.post")
    def test_any_other_refusal_reports_the_status(self, mock_post):
        mock_post.return_value = response(401)

        with self.assertRaises(BridgeError) as ctx:
            bridge._provision(make_session(), "")

        self.assertEqual(str(ctx.exception), "Could not start the call (401)")


class SignalingPostTest(unittest.TestCase):
    """Tests for the per-call signalling requests."""

    @patch("poly.call.bridge.requests.post")
    def test_authenticates_with_the_call_token(self, mock_post):
        mock_post.return_value = response(200, {"sdp": "answer"})

        result = bridge._signaling_post(BRIDGE + "/sdp", "call-token", {"sdp": "offer"}, "connect")

        self.assertEqual(result, {"sdp": "answer"})
        _args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"], {"X-Call-Token": "call-token"})
        self.assertEqual(kwargs["json"], {"token": "call-token", "sdp": "offer"})

    @patch("poly.call.bridge.requests.post")
    def test_an_empty_success_body_is_an_empty_result(self, mock_post):
        mock_post.return_value = response(204)

        self.assertEqual(bridge._signaling_post(BRIDGE + "/sdp", "t", {}, "audio setup"), {})

    @patch("poly.call.bridge.requests.post")
    def test_a_rejected_step_is_named(self, mock_post):
        mock_post.return_value = response(404)

        with self.assertRaises(BridgeError) as ctx:
            bridge._signaling_post(BRIDGE + "/sdp", "t", {}, "connect")

        self.assertIn("connect", str(ctx.exception))
        self.assertIn("404", str(ctx.exception))

    @patch("poly.call.bridge.requests.delete")
    def test_teardown_deletes_the_call_with_its_token(self, mock_delete):
        creds = parse_provision_response(provision_payload())

        bridge._delete_call(make_session(), creds)

        args, kwargs = mock_delete.call_args
        self.assertEqual(args[0], BRIDGE + "/api/v1/call/LOCAL-1")
        self.assertEqual(kwargs["headers"], {"X-Call-Token": "call-token"})


class FakePeerConnection:
    """Stands in for the peer connection: records each step and reports a state.

    ``state_after_answer`` is the connection state reported once the answer to the
    first offer is applied; ``None`` leaves the connection waiting forever.
    """

    def __init__(self, configuration=None, state_after_answer="connected"):
        self.configuration = configuration
        self.state_after_answer = state_after_answer
        self.connectionState = "new"
        self.localDescription = None
        self.steps: list[tuple[str, str]] = []
        self.handlers: dict = {}
        self.track = None
        self.closed = False
        self._answers = 0

    def on(self, event):
        def register(handler):
            self.handlers[event] = handler
            return handler

        return register

    def addTrack(self, track):
        self.track = track

    def getTransceivers(self):
        transceiver = MagicMock()
        transceiver.sender.track = self.track
        transceiver.mid = "0"
        return [transceiver]

    async def createOffer(self):
        return MagicMock(sdp="caller-offer", type="offer")

    async def createAnswer(self):
        self._answers += 1
        return MagicMock(sdp=f"caller-answer-{self._answers}", type="answer")

    async def setLocalDescription(self, description):
        self.localDescription = description
        self.steps.append(("local", description.sdp))

    async def setRemoteDescription(self, description):
        self.steps.append((f"remote-{description.type}", description.sdp))
        if description.type == "answer" and self.state_after_answer:
            await self.set_state(self.state_after_answer)

    async def set_state(self, state):
        self.connectionState = state
        await self.handlers["connectionstatechange"]()

    async def close(self):
        self.closed = True


class FakeEventsSocket:
    """Stands in for the events socket: yields the given events, then closes.

    With ``hold_open`` it stays open after the events instead, as a live call does.
    """

    def __init__(self, events=(), hold_open=False):
        self._events = [json.dumps(event) for event in events]
        self._hold_open = hold_open
        self.sent: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._events:
            return self._events.pop(0)
        if self._hold_open:
            await asyncio.Event().wait()
        raise StopAsyncIteration


class RunBridgeCallTest(unittest.TestCase):
    """Tests for run_bridge_call: the whole exchange against a scripted bridge."""

    def setUp(self):
        self.posts: list[tuple[str, dict]] = []
        self.statuses: dict[str, int] = {}
        self.pull_payload = {"sdp": "agent-offer", "tracks": [{"trackName": "agent", "mid": "1"}]}
        self.pc = FakePeerConnection()
        self.socket = FakeEventsSocket()
        self.source = MagicMock()
        self.agent_tracks: list = []
        self.started: list[str] = []
        self.stop = asyncio.Event()

        patches = [
            patch("poly.call.bridge.requests.post", side_effect=self._post),
            patch("poly.call.bridge.requests.delete"),
            patch("poly.call.bridge.RTCPeerConnection", side_effect=self._new_pc),
            patch("poly.call.bridge.websockets.connect", side_effect=self._connect_socket),
        ]
        _post, self.mock_delete, self.mock_pc_class, self.mock_ws_connect = (
            p.start() for p in patches
        )
        self.addCleanup(patch.stopall)

    def _new_pc(self, configuration=None):
        self.pc.configuration = configuration
        return self.pc

    def _connect_socket(self, url):
        self.socket.url = url
        return self.socket

    def _post(self, url, headers=None, json=None, **_kwargs):
        step = url.removeprefix(BRIDGE)
        self.posts.append((step, json))
        status = self.statuses.get(step, 200)
        if status != 200:
            return response(status)
        if step == "/api/v1/call":
            return response(200, provision_payload())
        if step.endswith("/sdp"):
            return response(200, {"sdp": "bridge-answer"})
        if step.endswith("/sdp/pull"):
            return response(200, self.pull_payload)
        return response(204)

    def _run(self, **overrides):
        kwargs = {
            "source": self.source,
            "on_agent_track": self.agent_tracks.append,
            "stop": self.stop,
            "on_started": self.started.append,
        }
        kwargs.update(overrides)
        return asyncio.run(run_bridge_call(make_session(), "user@example.com", **kwargs))

    def _steps(self) -> list[str]:
        return [step for step, _body in self.posts]

    def test_runs_the_whole_exchange_and_returns_the_call_id(self):
        call_id = self._run()

        self.assertEqual(call_id, "LOCAL-1")
        self.assertEqual(
            self._steps(),
            [
                "/api/v1/call",
                "/api/v1/call/LOCAL-1/sdp",
                "/api/v1/call/LOCAL-1/sdp/pull",
                "/api/v1/call/LOCAL-1/sdp/renegotiate",
            ],
        )
        self.assertEqual(self.started, ["LOCAL-1"])

    def test_sends_the_caller_audio_in_a_complete_first_offer(self):
        self._run()

        self.assertIs(self.pc.track, self.source)
        _step, connect_body = self.posts[1]
        self.assertEqual(connect_body, {"token": "call-token", "sdp": "caller-offer", "mid": "0"})
        self.assertEqual(self.pc.steps[:2], [("local", "caller-offer"), ("remote-answer", "bridge-answer")])

    def test_answers_the_offer_that_adds_the_agent_audio(self):
        self._run()

        self.assertEqual(
            self.pc.steps[2:], [("remote-offer", "agent-offer"), ("local", "caller-answer-1")]
        )
        _step, renegotiate_body = self.posts[3]
        self.assertEqual(renegotiate_body, {"token": "call-token", "sdp": "caller-answer-1"})

    def test_uses_the_ice_servers_the_bridge_sent(self):
        self._run()

        servers = self.pc.configuration.iceServers
        self.assertEqual([server.urls for server in servers], ["stun:stun.example:3478"])

    def test_authenticates_the_events_socket_with_its_first_frame(self):
        self._run()

        self.assertEqual(
            self.socket.url, "wss://api.test.poly.ai/webrtc-bridge/api/v1/call/LOCAL-1/events"
        )
        self.assertEqual(self.socket.sent, [{"type": "auth", "token": "call-token"}])

    def test_hands_agent_audio_tracks_to_the_caller(self):
        self._run()
        audio, video = MagicMock(kind="audio"), MagicMock(kind="video")

        self.pc.handlers["track"](audio)
        self.pc.handlers["track"](video)

        self.assertEqual(self.agent_tracks, [audio])

    def test_a_repull_event_pulls_the_agent_audio_again(self):
        self.socket = FakeEventsSocket(events=[{"event": "unmute"}, {"event": "repull"}])

        self._run()

        self.assertEqual(self._steps().count("/api/v1/call/LOCAL-1/sdp/pull"), 2)
        self.assertEqual(self._steps().count("/api/v1/call/LOCAL-1/sdp/renegotiate"), 2)
        self.assertEqual(self.pc.steps[-1], ("local", "caller-answer-2"))

    def test_an_unreadable_event_is_ignored(self):
        self.socket = FakeEventsSocket()
        self.socket._events = ["not json", "[]"]

        self.assertEqual(self._run(), "LOCAL-1")
        self.assertEqual(self._steps().count("/api/v1/call/LOCAL-1/sdp/pull"), 1)

    def test_nothing_to_pull_skips_the_renegotiation(self):
        self.pull_payload = {}

        self._run()

        self.assertNotIn("/api/v1/call/LOCAL-1/sdp/renegotiate", self._steps())
        self.assertEqual(self.started, ["LOCAL-1"])

    def test_tears_the_call_down_when_it_ends(self):
        self._run()

        args, kwargs = self.mock_delete.call_args
        self.assertEqual(args[0], BRIDGE + "/api/v1/call/LOCAL-1")
        self.assertEqual(kwargs["headers"], {"X-Call-Token": "call-token"})
        self.assertTrue(self.pc.closed)

    def test_hanging_up_ends_a_live_call(self):
        self.socket = FakeEventsSocket(hold_open=True)

        call_id = self._run(on_started=lambda _call_id: self.stop.set())

        self.assertEqual(call_id, "LOCAL-1")
        self.mock_delete.assert_called_once()
        self.assertTrue(self.pc.closed)

    def test_a_connection_lost_mid_call_is_an_error(self):
        self.socket = FakeEventsSocket(hold_open=True)

        def lose_connection(_call_id):
            asyncio.ensure_future(self.pc.set_state("failed"))

        with self.assertRaises(BridgeError) as ctx:
            self._run(on_started=lose_connection)

        self.assertEqual(str(ctx.exception), "Connection failed")
        self.mock_delete.assert_called_once()
        self.assertTrue(self.pc.closed)

    @patch("poly.call.bridge._CONNECT_TIMEOUT_SECONDS", 0.01)
    def test_audio_that_never_connects_times_out_and_tears_down(self):
        self.pc.state_after_answer = None

        with self.assertRaises(BridgeError) as ctx:
            self._run()

        self.assertIn("Timed out", str(ctx.exception))
        self.assertEqual(self.started, [])
        self.mock_delete.assert_called_once()
        self.assertTrue(self.pc.closed)

    def test_a_rejected_connect_step_tears_down(self):
        self.statuses["/api/v1/call/LOCAL-1/sdp"] = 404

        with self.assertRaises(BridgeError) as ctx:
            self._run()

        self.assertIn("connect", str(ctx.exception))
        self.mock_ws_connect.assert_not_called()
        self.mock_delete.assert_called_once()
        self.assertTrue(self.pc.closed)

    def test_a_refused_call_opens_no_connection(self):
        self.statuses["/api/v1/call"] = 401

        with self.assertRaises(BridgeError):
            self._run()

        self.mock_pc_class.assert_not_called()
        self.mock_delete.assert_not_called()

    def test_an_unreachable_bridge_is_a_bridge_error(self):
        with patch(
            "poly.call.bridge.requests.post",
            side_effect=requests.ConnectionError("no route"),
        ):
            with self.assertRaises(BridgeError) as ctx:
                self._run()

        self.assertIn("Could not reach the call service", str(ctx.exception))
        self.mock_pc_class.assert_not_called()

    def test_losing_the_bridge_mid_setup_is_a_bridge_error(self):
        def post(url, **kwargs):
            if url.endswith("/sdp/pull"):
                raise requests.Timeout("slow")
            return self._post(url, **kwargs)

        with patch("poly.call.bridge.requests.post", side_effect=post):
            with self.assertRaises(BridgeError) as ctx:
                self._run()

        self.assertIn("Lost contact with the call service", str(ctx.exception))
        self.assertTrue(self.pc.closed)


if __name__ == "__main__":
    unittest.main()

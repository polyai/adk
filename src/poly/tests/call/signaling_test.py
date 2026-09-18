"""Tests for the WebRTC signaling protocol.

Copyright PolyAI Limited
"""

import unittest

from poly.call.session import DEFAULT_CALL_MODE, CallSession
from poly.call.signaling import (
    SIGNALING_PATH,
    AnswerMessage,
    CloseMessage,
    ErrorMessage,
    IceCandidateMessage,
    SignalingMessageType,
    build_offer_message,
    parse_message,
    signaling_url,
)


def make_session(variant_id: str = "") -> CallSession:
    """Build a CallSession fixture."""
    return CallSession(
        account_id="acc-1",
        project_id="proj-1",
        variant_id=variant_id,
        artifact_version="artifact-v1",
        lambda_deployment_version="lambda-v1",
        auth_token="studio-token",
        gateway_ws_url="wss://webrtc-gateway.test.polyai.app",
        mode=DEFAULT_CALL_MODE,
    )


class SignalingUrlTest(unittest.TestCase):
    """Tests for signaling_url."""

    def test_appends_signaling_path(self):
        self.assertEqual(
            signaling_url("wss://webrtc-gateway.test.polyai.app"),
            f"wss://webrtc-gateway.test.polyai.app{SIGNALING_PATH}",
        )

    def test_strips_trailing_slash(self):
        self.assertEqual(
            signaling_url("wss://gw.example/"),
            f"wss://gw.example{SIGNALING_PATH}",
        )


class BuildOfferMessageTest(unittest.TestCase):
    """Tests for build_offer_message."""

    def test_draft_offer_shape(self):
        session = make_session()

        offer = build_offer_message(session, sdp="v=0...", caller="dev@poly.ai")

        self.assertEqual(offer["type"], SignalingMessageType.OFFER.value)
        self.assertEqual(offer["sessionId"], "")
        self.assertEqual(offer["data"], {"type": "offer", "sdp": "v=0..."})
        self.assertEqual(offer["caller"], "dev@poly.ai")
        self.assertEqual(offer["mode"], DEFAULT_CALL_MODE)
        self.assertEqual(offer["authToken"], "studio-token")
        self.assertEqual(offer["accountId"], "acc-1")
        self.assertEqual(offer["projectId"], "proj-1")
        self.assertEqual(
            offer["agentVersionOverride"],
            {"artifactVersion": "artifact-v1", "lambdaDeploymentVersion": "lambda-v1"},
        )

    def test_generated_call_sid_is_prefixed(self):
        offer = build_offer_message(make_session(), sdp="s", caller="c")
        self.assertTrue(offer["callSid"].startswith("ADK-"))

    def test_explicit_call_sid_is_used(self):
        offer = build_offer_message(make_session(), sdp="s", caller="c", call_sid="ADK-fixed")
        self.assertEqual(offer["callSid"], "ADK-fixed")

    def test_variant_id_omitted_when_empty(self):
        offer = build_offer_message(make_session(variant_id=""), sdp="s", caller="c")
        self.assertNotIn("variantId", offer)

    def test_variant_id_included_when_set(self):
        offer = build_offer_message(make_session(variant_id="VARIANT-x"), sdp="s", caller="c")
        self.assertEqual(offer["variantId"], "VARIANT-x")


class ParseMessageTest(unittest.TestCase):
    """Tests for parse_message."""

    def test_parses_answer(self):
        msg = parse_message(
            {"type": "answer", "sessionId": "sess-1", "data": {"type": "answer", "sdp": "a"}}
        )
        self.assertEqual(msg, AnswerMessage(session_id="sess-1", sdp="a"))

    def test_parses_ice_candidate(self):
        candidate = {"candidate": "candidate:...", "sdpMid": "0", "sdpMLineIndex": 0}
        msg = parse_message({"type": "ice-candidate", "sessionId": "sess-1", "data": candidate})
        self.assertEqual(msg, IceCandidateMessage(session_id="sess-1", candidate=candidate))

    def test_parses_error_with_data_nesting(self):
        # The gateway's actual wire format: code/message under `data`.
        msg = parse_message(
            {
                "type": "error",
                "sessionId": "sess-1",
                "data": {"code": "FORBIDDEN", "message": "Echo mode requires debug mode"},
            }
        )
        self.assertEqual(
            msg,
            ErrorMessage(
                session_id="sess-1",
                code="FORBIDDEN",
                message="Echo mode requires debug mode",
            ),
        )

    def test_parses_error_with_top_level_fallback(self):
        msg = parse_message(
            {
                "type": "error",
                "sessionId": "sess-1",
                "code": "UNAUTHORIZED",
                "message": "bad token",
            }
        )
        self.assertEqual(
            msg,
            ErrorMessage(session_id="sess-1", code="UNAUTHORIZED", message="bad token"),
        )

    def test_parses_close(self):
        msg = parse_message({"type": "close", "sessionId": "sess-1"})
        self.assertEqual(msg, CloseMessage(session_id="sess-1"))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            parse_message({"type": "bogus", "sessionId": "sess-1"})

    def test_missing_type_raises(self):
        with self.assertRaises(ValueError):
            parse_message({"sessionId": "sess-1"})


if __name__ == "__main__":
    unittest.main()

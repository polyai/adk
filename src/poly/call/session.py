"""Data structures describing a bootstrapped voice call session."""

from dataclasses import dataclass

# The call mode sent in the OFFER. The WebRTC gateway resolves the *effective* mode
# per-agent from LLeMur config and largely ignores this value — it's only the fallback
# the gateway applies if that config lookup fails. We send "end-to-end" to match the
# in-browser Agent Studio call panel, which always sends that mode.
DEFAULT_CALL_MODE = "end-to-end"


@dataclass(frozen=True)
class CallSession:
    """Everything needed to open a WebRTC call to a draft/branch build.

    These fields populate the signaling OFFER sent to the WebRTC gateway.

    Attributes:
        account_id: The PolyAI account ID.
        project_id: The agent/project ID.
        variant_id: The variant ID, or an empty string if none.
        artifact_version: The prepared draft artifact version.
        lambda_deployment_version: The prepared draft lambda deployment version.
        auth_token: The studio token authorizing the call at the gateway.
        gateway_ws_url: The WebRTC signaling gateway base.
        mode: The call mode.
    """

    account_id: str
    project_id: str
    variant_id: str
    artifact_version: str
    lambda_deployment_version: str
    auth_token: str
    gateway_ws_url: str
    mode: str = DEFAULT_CALL_MODE

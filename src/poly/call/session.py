"""Data structures describing a bootstrapped voice call session."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CallSession:
    """Everything needed to open a WebRTC call to a draft/branch build.

    The studio token names the account, project and prepared build, so the call
    service takes those from it rather than from the caller.

    Attributes:
        account_id: The PolyAI account ID.
        project_id: The agent/project ID.
        variant_id: The variant ID, or an empty string if none.
        auth_token: The studio token authorizing the call.
        bridge_url: The base URL of the WebRTC bridge that places the call.
    """

    account_id: str
    project_id: str
    variant_id: str
    auth_token: str
    bridge_url: str

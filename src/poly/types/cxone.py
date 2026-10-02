# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from typing import Any


__all__ = [
    "CxOne",
    "CxOneError",
    "CxOneMissingContactId",
    "CxOneSecretError",
    "CxOneSignalError",
    "CxOneTokenError",
]

DEFAULT_TOKEN_URL = "https://cxone.niceincontact.com/auth/token"
DEFAULT_REGION = "na1"
DEFAULT_DOMAIN = "niceincontact"
DEFAULT_VERSION = "v24.0"
DEFAULT_TIMEOUT_SECONDS = 10.0
UNAUTHORIZED = 401
CONTACT_ID_HEADERS = ("X-InContact-ContactId", "X-inc-master-id")
MAX_SIGNAL_PARAMETERS = 9


class CxOneError(Exception):
    """Base class for CXone errors."""


class CxOneMissingContactId(CxOneError):
    """No CXone contact ID was given and none could be read from SIP headers."""

    def __init__(self, headers: tuple[str, ...] = ...): ...


class CxOneSecretError(CxOneError):
    """The CXone credentials secret is missing, inaccessible or malformed."""

    def __init__(self, secret_name: str, reason: str): ...


class CxOneTokenError(CxOneError):
    """CXone rejected the request for an access token."""

    def __init__(self, status_code: int, detail: str): ...


class CxOneSignalError(CxOneError):
    """The CXone Signal API returned an error."""

    def __init__(self, status_code: int, detail: str): ...


class CxOne:
    """CXone Signal API interface, exposed to functions as ``conv.cxone``."""

    def __init__(self, conv: Any):
        """init"""

    @property
    def default_secret_name(self) -> str:
        """Name of the CXone credentials secret used when none is given."""

    @property
    def contact_id(self) -> str | None:
        """The CXone contact ID from the inbound SIP headers, if present."""

    def handoff(
        self,
        reason: str | None = ...,
        params: dict[str, Any] | list[Any] | None = ...,
        contact_id: str | None = ...,
        destination: str | None = ...,
        utterance: str | None = ...,
        region: str = ...,
        domain: str = ...,
        version: str = ...,
        secret_name: str | None = ...,
        token_url: str = ...,
        timeout: float = ...,
    ) -> None:
        """Hand the caller back to CXone and end PolyAI's leg of the call."""

    def signal(
        self,
        params: dict[str, Any] | list[Any] | None = ...,
        contact_id: str | None = ...,
        region: str = ...,
        domain: str = ...,
        version: str = ...,
        secret_name: str | None = ...,
        token_url: str = ...,
        timeout: float = ...,
    ) -> None:
        """Send a signal to the CXone Studio script without ending the call."""


__all__ = [
    "CxOne",
    "CxOneError",
    "CxOneMissingContactId",
    "CxOneSecretError",
    "CxOneSignalError",
    "CxOneTokenError",
]

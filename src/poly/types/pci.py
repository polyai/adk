# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = [
    "PciError",
    "PciNotConfigured",
    "PciBadRequest",
    "PciCaptureNotFound",
    "PciConflict",
    "PciAttemptMismatch",
    "PciCaptureExpired",
    "PciRateLimited",
    "PciResultUnknown",
    "PciTimeout",
    "PciUnavailable",
]

from collections.abc import Callable
from typing import Any


class PciError(Exception):
    status: Any
    error: Any
    field: Any
    retryable: Any
    retry_after: Any

    def __init__(
        self,
        message: str,
        status: int | None = None,
        error: str | None = None,
        retryable: bool = False,
        retry_after: int | None = None,
        field: str | None = None,
    ) -> None: ...


class PciNotConfigured(PciError): ...


class PciInsecureTransport(PciNotConfigured): ...


class PciBadRequest(PciError): ...


class PciCaptureNotFound(PciError): ...


class PciConflict(PciError): ...


class PciAttemptMismatch(PciConflict): ...


class PciCaptureExpired(PciError): ...


class PciResultUnknown(PciCaptureExpired): ...


class PciRateLimited(PciError): ...


class PciUnavailable(PciError): ...


class PciTimeout(PciUnavailable): ...


def idempotency_key(attempt_id: str) -> str: ...
def capture_id_for(call_sid: str) -> str: ...


class PCI:
    call_sid: Any
    base_url: Any

    def __init__(
        self,
        call_sid: str,
        token: str | None,
        base_url: str = ...,
        is_event_registered: Callable[[str], bool] | None = None,
    ) -> None: ...
    def __reduce__(self) -> None: ...
    @property
    def capture_id(self) -> str: ...
    def arm(self, wait_ms: int = ...) -> dict[str, Any]: ...
    def status(self) -> dict[str, Any]: ...
    def collect(
        self,
        name: str,
        format: str | None = None,
        wait_ms: int = ...,
        ext_event_id: str | None = None,
    ) -> dict[str, Any]: ...
    def field(self, name: str) -> dict[str, Any]: ...
    def erase(self, name: str) -> None: ...
    def submit(
        self,
        payment_interface: str,
        *,
        attempt_id: str,
        amount_minor: int | None = None,
        currency: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        zip_code: str | None = None,
        wait_ms: int = 0,
    ) -> dict[str, Any]: ...
    def result(self, submission_id: str | None = None) -> dict[str, Any]: ...
    def disarm(self, attempt_id: str | None = None) -> None: ...

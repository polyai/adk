# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = [
    "CxOne",
    "CxOneError",
    "CxOneMissingContactId",
    "CxOneSecretError",
    "CxOneSignalError",
    "CxOneTokenError",
]

from typing import Any

__all__ = [
    "CxOneError",
    "CxOneMissingContactId",
    "CxOneSecretError",
    "CxOneTokenError",
    "CxOneSignalError",
    "CxOne",
]


class CxOneError(Exception): ...


class CxOneMissingContactId(CxOneError):
    def __init__(self, headers: tuple[str, ...] = ...) -> None: ...


class CxOneSecretError(CxOneError):
    secret_name: Any

    def __init__(self, secret_name: str, reason: str) -> None: ...


class CxOneTokenError(CxOneError):
    status_code: Any

    def __init__(self, status_code: int, detail: str) -> None: ...


class CxOneSignalError(CxOneError):
    status_code: Any

    def __init__(self, status_code: int, detail: str) -> None: ...


class CxOne:
    def __init__(self, conv: Any) -> None: ...
    @property
    def default_secret_name(self) -> str: ...
    @property
    def contact_id(self) -> str | None: ...
    def handoff(
        self,
        reason: str | None = None,
        params: dict[str, Any] | list[Any] | None = None,
        contact_id: str | None = None,
        destination: str | None = None,
        utterance: str | None = None,
        region: str = ...,
        domain: str = ...,
        version: str = ...,
        secret_name: str | None = None,
        token_url: str = ...,
        timeout: float = ...,
    ) -> None: ...
    def signal(
        self,
        params: dict[str, Any] | list[Any] | None = None,
        contact_id: str | None = None,
        region: str = ...,
        domain: str = ...,
        version: str = ...,
        secret_name: str | None = None,
        token_url: str = ...,
        timeout: float = ...,
    ) -> None: ...

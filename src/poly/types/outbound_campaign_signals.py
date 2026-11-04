# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = ["OutboundCampaignSignals", "SignalResult"]

from dataclasses import dataclass
from typing import Any

MAX_SIGNAL_BODY_BYTES: Any = ...
MAX_SIGNALS_PER_INVOCATION: int = ...


@dataclass(frozen=True)
class SignalResult:
    status: str
    reason: str | None = ...

    @property
    def applied(self) -> bool: ...


class OutboundCampaignSignals:
    def __init__(self, conv: Any, token: Any, url: Any) -> None: ...
    def __reduce__(self) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def update_journey_state(
        self, state: dict[str, Any] | None = None, result: str | None = None
    ) -> SignalResult: ...
    def update_dnc(
        self, action: str, scope: str | None = None, channels: str | list[str] | None = None
    ) -> SignalResult: ...
    def flush_logs(self) -> None: ...

# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = ["Clock"]

from datetime import date, datetime

DEFAULT_TIMEZONE: str = ...


class Clock:
    def __init__(self, instant: datetime | None = None, timezone: str | None = None) -> None: ...
    def now(self) -> datetime: ...
    def now_utc(self) -> datetime: ...
    def today(self) -> date: ...
    @property
    def timezone(self) -> str: ...

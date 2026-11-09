# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

from typing import Any

HIDDEN_FIELDS: dict[str, frozenset[str]] = ...


def sanitise(values: Any) -> Any: ...

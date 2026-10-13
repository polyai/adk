# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

import pickle
from typing import Any


def encode_state_value(v: Any, pickler: type[pickle.Pickler] | None = None) -> str: ...
def pickle_state(state: dict, pickler: type[pickle.Pickler] | None = None) -> dict[str, str]: ...
def json_project_state(state: dict) -> dict[str, Any]: ...
def unpickle_state(d: dict[str, str]) -> dict[str, Any]: ...

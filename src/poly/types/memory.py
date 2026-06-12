# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from typing import Any


__all__ = ["Memory"]


class Memory:
    """An object exposing fields in the agent memory."""

    def __init__(self, fields: dict[str, Any]):
        """init"""

    def __getitem__(self, name: str) -> Any:
        """Get a field from memory."""

    def get(self, name: str, default: Any = ...) -> Any | None:
        """Get a field from memory."""

    def __contains__(self, name: str) -> bool:
        """Check if a field is populated in memory."""

    def __len__(self) -> int:
        """Get the number of fields in memory."""

    def fields(self) -> dict:
        """Get all the fields from memory."""

    def __setattr__(self, name: str, value: Any):
        """WARNING: Do not use this method, this object is read-only."""

    def __setitem__(self, name: str, value):
        """WARNING: Do not use this method, this object is read-only."""

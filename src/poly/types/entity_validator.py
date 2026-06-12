# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from runtime.value_extraction_types import EntityType


__all__ = ["EntityValidationResult"]


class EntityValidationResult:
    """Entity validation result"""

    id: str
    name: str
    valid: bool
    value: str
    type: EntityType
    error: str | None

    def __init__(
        self, id: str, name: str, valid: bool, value: str, type: EntityType, error: str | None = ...
    ) -> None: ...
    def to_dict(self) -> dict:
        """Convert to dict"""

    @classmethod
    def from_dict(cls, d: dict) -> EntityValidationResult:
        """Convert from dict"""

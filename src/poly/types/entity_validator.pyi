# Copyright PolyAI Limited
from dataclasses import dataclass
from .value_extraction_types import EntityType

@dataclass
class EntityValidationResult:
    id: str
    name: str
    valid: bool
    value: str
    type: EntityType
    error: str | None = ...
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> EntityValidationResult: ...

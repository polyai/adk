"""Handling and managing Agent Studio Transcript Corrections (ASR Corrections)

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.transcript_corrections_pb2 import (
    RegularExpression as RegularExpressionProto,
)
from poly.handlers.protobuf.transcript_corrections_pb2 import (
    TranscriptCorrection as TranscriptCorrectionProto,
)
from poly.handlers.protobuf.transcript_corrections_pb2 import (
    TranscriptCorrections_CreateTranscriptCorrections,
    TranscriptCorrections_DeleteTranscriptCorrections,
    TranscriptCorrections_UpdateTranscriptCorrections,
    TranscriptCorrectionsUpdateData,
)
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping

VALID_REPLACEMENT_TYPES = ("full", "partial", "substring")


@dataclass
class RegularExpressionRule:
    """A single regex replacement rule within a transcript correction."""

    regular_expression: str
    replacement: str
    replacement_type: str = "full"

    def to_yaml_dict(self) -> dict:
        return {
            "regular_expression": self.regular_expression,
            "replacement": self.replacement,
            "replacement_type": self.replacement_type,
        }

    def to_proto(self, rule_id: str = "") -> RegularExpressionProto:
        return RegularExpressionProto(
            id=rule_id,
            regular_expression=self.regular_expression,
            replacement=self.replacement,
            replacement_type=self.replacement_type,
        )

    @classmethod
    def from_yaml_dict(cls, yaml_dict: dict) -> "RegularExpressionRule":
        replacement_type = yaml_dict.get("replacement_type", "full")
        if replacement_type == "substring":
            # Substring in the FE, "partial" in the BE
            replacement_type = "partial"

        return cls(
            regular_expression=yaml_dict.get("regular_expression", ""),
            replacement=yaml_dict.get("replacement", ""),
            replacement_type=replacement_type,
        )


@dataclass
class TranscriptCorrection(MultiResourceYamlResource):
    """Dataclass representing an ASR Transcript Correction"""

    projection_path: ClassVar[list[str]] = [
        "transcriptCorrections",
        "transcriptCorrections",
        "entities",
        "{id}",
    ]

    description: str
    regular_expressions: list[RegularExpressionRule] = field(default_factory=list)
    top_level_name: ClassVar[str] = "corrections"

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        regular_expressions: Optional[list] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description

        raw_rules = regular_expressions or []
        self.regular_expressions = [
            r if isinstance(r, RegularExpressionRule) else RegularExpressionRule.from_yaml_dict(r)
            for r in raw_rules
        ]

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "voice",
            "speech_recognition",
            "transcript_corrections.yaml",
            self.top_level_name,
            path_safe_name,
        )

    def to_yaml_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "regular_expressions": [r.to_yaml_dict() for r in self.regular_expressions],
        }
        return {k: v for k, v in d.items() if v != "" and v is not None}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "TranscriptCorrection":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name", name),
            description=(yaml_dict.get("description") or "").strip(),
            regular_expressions=yaml_dict.get("regular_expressions", []),
        )

    @property
    def command_type(self) -> str:
        return "transcript_corrections"

    def _build_regex_protos(self) -> list[RegularExpressionProto]:
        return [
            rule.to_proto(rule_id=f"{self.resource_id}-REGEX-{idx}")
            for idx, rule in enumerate(self.regular_expressions)
        ]

    def _build_correction_proto(self) -> TranscriptCorrectionProto:
        return TranscriptCorrectionProto(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            regular_expressions=self._build_regex_protos(),
        )

    def build_create_proto(self) -> TranscriptCorrections_CreateTranscriptCorrections:
        return TranscriptCorrections_CreateTranscriptCorrections(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            regular_expressions=self._build_regex_protos(),
        )

    def build_update_proto(self) -> TranscriptCorrections_UpdateTranscriptCorrections:
        return TranscriptCorrections_UpdateTranscriptCorrections(
            data=TranscriptCorrectionsUpdateData(
                corrections=[self._build_correction_proto()],
            ),
        )

    def build_delete_proto(self) -> TranscriptCorrections_DeleteTranscriptCorrections:
        return TranscriptCorrections_DeleteTranscriptCorrections(
            transcript_corrections_id=self.resource_id,
        )

    def validate(self, **kwargs) -> None:
        if not self.name:
            raise ValueError("Correction name is required")
        if not self.regular_expressions:
            raise ValueError("At least one regular expression rule is required")
        for idx, rule in enumerate(self.regular_expressions):
            if not rule.regular_expression:
                raise ValueError(f"Regular expression is required for rule {idx}")
            if rule.replacement_type not in VALID_REPLACEMENT_TYPES:
                raise ValueError(
                    f"Invalid replacement_type '{rule.replacement_type}' in rule {idx}. "
                    f"Must be one of: {', '.join(VALID_REPLACEMENT_TYPES)}"
                )

    @classmethod
    def validate_collection(
        cls,
        resources: dict[str, "TranscriptCorrection"],
        resource_mappings: list[ResourceMapping] | None = None,
        **kwargs,
    ) -> None:
        seen = set()
        duplicates = set()

        for c in resources.values():
            if c.name in seen:
                duplicates.add(c.name)
            else:
                seen.add(c.name)

        if duplicates:
            raise ValueError(f"Duplicate transcript correction names: {sorted(duplicates)}")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        yaml_path = os.path.join(
            base_path, "voice", "speech_recognition", "transcript_corrections.yaml"
        )
        discovered: list[str] = []

        if not os.path.exists(yaml_path):
            return discovered

        yaml_dict = TranscriptCorrection._get_top_level_data(yaml_path)
        corrections: list[dict] = yaml_dict.get("corrections", []) if yaml_dict else []

        for correction in corrections:
            name = correction.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered.append(
                os.path.join(yaml_path, TranscriptCorrection.top_level_name, path_safe_name)
            )

        return discovered

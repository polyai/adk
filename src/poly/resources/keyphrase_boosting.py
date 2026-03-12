"""Handling and managing Agent Studio Keyphrase Boosting (ASR Keyphrases)

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.keyphrase_boosting_pb2 import (
    KeyphraseBoosting_CreateKeyphrase,
    KeyphraseBoosting_DeleteKeyphrase,
    KeyphraseBoosting_UpdateKeyphrase,
)
from poly.resources.resource import MultiResourceYamlResource

VALID_LEVELS = ("default", "boosted", "maximum")


@dataclass
class KeyphraseBoosting(MultiResourceYamlResource):
    """Dataclass representing an ASR Keyphrase Boosting entry"""

    keyphrase: str
    level: str
    top_level_name: ClassVar[str] = "keyphrases"

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        keyphrase: str = "",
        level: str = "default",
    ):
        self.resource_id = resource_id
        self.name = name
        self.keyphrase = keyphrase
        self.level = level.lower()

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "voice",
            "speech_recognition",
            "keyphrase_boosting.yaml",
            self.top_level_name,
            path_safe_name,
        )

    def to_yaml_dict(self) -> dict:
        return {
            "keyphrase": self.keyphrase,
            "level": self.level,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "KeyphraseBoosting":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("keyphrase", name),
            keyphrase=yaml_dict.get("keyphrase", ""),
            level=yaml_dict.get("level", "default").lower(),
        )

    @property
    def command_type(self) -> str:
        return "keyphrase_boosting"

    def build_create_proto(self) -> KeyphraseBoosting_CreateKeyphrase:
        return KeyphraseBoosting_CreateKeyphrase(
            id=self.resource_id,
            keyphrase=self.keyphrase,
            level=self.level,
        )

    def build_update_proto(self) -> KeyphraseBoosting_UpdateKeyphrase:
        return KeyphraseBoosting_UpdateKeyphrase(
            id=self.resource_id,
            keyphrase=self.keyphrase,
            level=self.level,
        )

    def build_delete_proto(self) -> KeyphraseBoosting_DeleteKeyphrase:
        return KeyphraseBoosting_DeleteKeyphrase(
            id=self.resource_id,
        )

    def validate(self, **kwargs) -> None:
        if not self.keyphrase:
            raise ValueError("Keyphrase is required")
        if self.level not in VALID_LEVELS:
            raise ValueError(
                f"Invalid level '{self.level}'. Must be one of: {', '.join(VALID_LEVELS)}"
            )

    @staticmethod
    def _find_matching(yaml_list, resource_clean_name) -> Optional[dict]:
        for r in yaml_list:
            if utils.clean_name(r.get("keyphrase") or "", lowercase=False) == resource_clean_name:
                return r
        return None

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        # Must match file_path: voice/speech_recognition/keyphrase_boosting.yaml
        # Also check legacy path: speech_recognition/keyphrase_boosting.yaml
        for rel_path in (
            os.path.join("voice", "speech_recognition", "keyphrase_boosting.yaml"),
            os.path.join("speech_recognition", "keyphrase_boosting.yaml"),
        ):
            yaml_path = os.path.join(base_path, rel_path)
            if os.path.exists(yaml_path):
                break
        else:
            return []

        discovered: list[str] = []
        yaml_dict = KeyphraseBoosting._get_top_level_data(yaml_path)
        keyphrases: list[dict] = yaml_dict.get("keyphrases", []) if yaml_dict else []

        for kp in keyphrases:
            name = kp.get("keyphrase")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered.append(
                os.path.join(yaml_path, KeyphraseBoosting.top_level_name, path_safe_name)
            )

        return discovered

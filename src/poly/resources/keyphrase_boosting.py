"""Handling and managing Agent Studio Keyphrase Boosting (ASR Keyphrases)

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.keyphrase_boosting_pb2 import (
    KeyphraseBoosting_CreateKeyphrase,
    KeyphraseBoosting_DeleteKeyphrase,
    KeyphraseBoosting_UpdateKeyphrase,
)
from poly.resources.resource import MultiResourceYamlResource, register_resource

logger = logging.getLogger(__name__)

VALID_LEVELS = ("default", "boosted", "maximum")


def _as_text(value: object) -> str:
    """Coerce a resolved YAML scalar back to the text the author wrote.

    The loader follows YAML 1.2, so a bare `true`/`false` resolves to a bool and
    a bare `2024` to an int. Boosting digits or years is a reasonable thing to
    want, and either type breaks the string handling below.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value if isinstance(value, str) else str(value)


def normalize_keyphrase(keyphrase: str) -> str:
    """Normalize a keyphrase for uniqueness comparison.

    Mirrors Agent Studio's `normalizeKeyphrase` (trim + lowercase). The platform
    rejects a whole command batch when two keyphrases normalize the same, so the
    ADK has to agree about what counts as a duplicate.
    """
    return keyphrase.strip().lower()


def _group_by_normalized(
    keyphrases: list[str],
) -> dict[str, list[str]]:
    """Group keyphrases by their normalized form, preserving original spellings."""
    groups: dict[str, list[str]] = {}
    for keyphrase in keyphrases:
        normalized = normalize_keyphrase(keyphrase)
        if not normalized:
            continue
        groups.setdefault(normalized, []).append(keyphrase)
    return groups


@register_resource("keyphrase_boosting")
@dataclass
class KeyphraseBoosting(MultiResourceYamlResource):
    """Dataclass representing an ASR Keyphrase Boosting entry"""

    keyphrase: str
    level: str
    top_level_name: ClassVar[str] = "keyphrases"
    resource_key: ClassVar[str] = "keyphrase"

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        keyphrase: str = "",
        level: str = "default",
    ):
        self.resource_id = resource_id
        self.name = _as_text(name)
        self.keyphrase = _as_text(keyphrase)
        self.level = level.lower()

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "KeyphraseBoosting"]:
        """Parse keyphrase boosting entries from a projection dict."""
        keyphrases = {}
        keyphrases_projection = (
            projection.get("keyphraseBoosting", {}).get("keyphraseBoosting", {}).get("entities", {})
        )
        if "keyphraseBoosting" not in projection or any(
            "keyphrase" not in kp for kp in keyphrases_projection.values()
        ):
            logger.debug("No read access to keyphrase boosting - it will not be pulled.")
            return {}

        for kp_id, kp_data in keyphrases_projection.items():
            keyphrases[kp_id] = cls(
                resource_id=kp_id,
                name=kp_data.get("keyphrase", ""),
                keyphrase=kp_data.get("keyphrase", ""),
                level=kp_data.get("level", "default"),
            )

        cls._warn_about_duplicates(keyphrases)
        return keyphrases

    @classmethod
    def _warn_about_duplicates(cls, keyphrases: dict[str, "KeyphraseBoosting"]) -> None:
        """Warn about keyphrases that normalize to the same phrase.

        Projects created before Agent Studio enforced uniqueness can still hold
        colliding entries. Pulling one must not fail, but the next push will, so
        flag them here while the original spellings are still visible.
        """
        for _, spellings in sorted(
            _group_by_normalized([k.keyphrase for k in keyphrases.values()]).items()
        ):
            if len(spellings) > 1:
                logger.warning(
                    "Keyphrases %s differ only by case or surrounding whitespace. "
                    "Agent Studio treats them as one phrase and will reject a push "
                    "that keeps both - remove the duplicates.",
                    " / ".join(repr(s) for s in sorted(spellings)),
                )

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

    @classmethod
    def validate_collection(
        cls,
        resources: dict[str, "KeyphraseBoosting"],
        **kwargs,
    ) -> None:
        """Reject keyphrases that collide once trimmed and lowercased.

        Agent Studio enforces this server-side and fails the entire push with an
        opaque entity id, so catch it here where the offending phrase can be named.
        """
        groups = _group_by_normalized([r.keyphrase for r in resources.values()])
        duplicates = {
            normalized: spellings for normalized, spellings in groups.items() if len(spellings) > 1
        }
        if not duplicates:
            return

        described = "; ".join(
            " / ".join(repr(s) for s in sorted(spellings))
            for _, spellings in sorted(duplicates.items())
        )
        raise ValueError(
            "Duplicate keyphrases (compared case-insensitively, ignoring surrounding "
            f"whitespace): {described}. Keep one entry per phrase."
        )

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
            name = _as_text(kp.get(KeyphraseBoosting.resource_key))
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered.append(
                os.path.join(yaml_path, KeyphraseBoosting.top_level_name, path_safe_name)
            )

        return discovered

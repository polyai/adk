"""Handling and managing Agent Studio Translations

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.translations_pb2 import (
    LanguageHubTranslations_Create,
    LanguageHubTranslations_Delete,
    LanguageHubTranslations_Update,
    LocalizedText,
    UpdateEntry,
)
from poly.resources.languages import AdditionalLanguage, DefaultLanguage
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping, register_resource

logger = logging.getLogger(__name__)


@register_resource("translations")
@dataclass
class Translation(MultiResourceYamlResource):
    """Dataclass representing an Agent Studio Translation"""

    translations: dict[str, str]
    top_level_name: ClassVar[str] = "translations"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "Translation"]:
        """Parse translations from a projection dict."""
        if "translations" not in projection:
            logger.debug("No read access to translations - it will not be pulled.")
            return {}

        translations_data = (
            projection.get("translations", {}).get("translations", {}).get("entities", {})
        )
        if not translations_data:
            return {}

        # Auth-filtered: keep id and translation key only, so {{tn:<id>}} in a
        # readable topic or behaviour rule still renders as a key, not a raw id.
        if any(
            "translations" not in translation_data
            for translation_data in translations_data.values()
        ):
            logger.debug("No read access to translations - keeping keys for references only.")
            return {
                translation_id: cls(
                    resource_id=translation_id,
                    name=translation_data.get("translationKey", ""),
                    slim=True,
                )
                for translation_id, translation_data in translations_data.items()
            }

        translations = {}
        for translation_id, translation_data in translations_data.items():
            translations[translation_id] = cls(
                resource_id=translation_id,
                name=translation_data.get("translationKey", ""),
                translations={
                    translation.get("languageCode"): translation.get("text", "")
                    for translation in translation_data.get("translations", [])
                },
            )
        return translations

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        translations: dict[str, str] = None,
        slim: bool = False,
    ):
        self.resource_id = resource_id
        self.name = name or ""
        self.translations = translations if translations is not None else {}
        self.slim = slim

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "config",
            "translations.yaml",
            self.top_level_name,
            path_safe_name,
        )

    @staticmethod
    def get_resource_prefix(**kwargs):
        return "tn"

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "Translation":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            translations=yaml_dict.get("translations", {}),
        )

    def to_yaml_dict(self) -> dict:
        return {
            "name": self.name,
            "translations": self.translations,
        }

    @property
    def command_type(self):
        return "translation"

    def build_create_proto(self):
        return LanguageHubTranslations_Create(
            id=self.resource_id,
            translation_key=self.name,
            translations=[
                LocalizedText(language_code=lang, text=text, is_auto_translated=False)
                for lang, text in self.translations.items()
            ],
        )

    def build_update_proto(self):
        return LanguageHubTranslations_Update(
            id=self.resource_id,
            translation_key=self.name,
            translations=[
                UpdateEntry(language_code=lang, text=text, is_auto_translated=False)
                for lang, text in self.translations.items()
            ],
        )

    def build_delete_proto(self):
        return LanguageHubTranslations_Delete(id=self.resource_id)

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        if not self.name:
            raise ValueError("Translation name cannot be empty.")
        if not self.translations:
            raise ValueError("Translations cannot be empty.")

        if resource_mappings:
            configured_languages = {
                m.resource_name
                for m in resource_mappings
                if m.resource_type in (DefaultLanguage, AdditionalLanguage)
            }
            if configured_languages:
                missing = configured_languages - set(self.translations.keys())
                if missing:
                    raise ValueError(
                        f"Missing translations for configured languages: {sorted(missing)}."
                    )
                extra = set(self.translations.keys()) - configured_languages
                if extra:
                    raise ValueError(f"Translation for language not configured: {sorted(extra)}.")

    @staticmethod
    def discover_resources(base_path):
        translations_path = os.path.join(base_path, "config", "translations.yaml")
        discovered_translations: list[str] = []

        if not os.path.exists(translations_path):
            return discovered_translations

        yaml_dict = Translation._get_top_level_data(translations_path)
        translations: list[dict] = yaml_dict.get("translations", []) if yaml_dict else []

        for translation in translations:
            name = translation.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_translations.append(
                os.path.join(translations_path, Translation.top_level_name, path_safe_name)
            )

        return discovered_translations

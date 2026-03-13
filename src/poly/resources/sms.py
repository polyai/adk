"""Handling and managing an Agent Studio SMS Templates

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.sms_pb2 import (
    SMS_CreateTemplate,
    SMS_DeleteTemplate,
    SMS_UpdateTemplate,
    SMSEnvPhoneNumbers,
    SMSTemplateReferences,
    UpdateSMSEnvPhoneNumbers,
)
from poly.resources.resource import MultiResourceYamlResource


@dataclass
class EnvPhoneNumbers:
    sandbox: str
    pre_release: str
    live: str

    def to_yaml_dict(self) -> dict:
        return {
            "sandbox": self.sandbox,
            "pre_release": self.pre_release,
            "live": self.live,
        }


@dataclass
class SMSTemplate(MultiResourceYamlResource):
    """SMS resource for ADK."""

    text: str
    env_phone_numbers: Optional[EnvPhoneNumbers]
    top_level_name: ClassVar[str] = "sms_templates"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        text: str,
        env_phone_numbers: EnvPhoneNumbers | dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.text = text
        if env_phone_numbers is None:
            self.env_phone_numbers = None
        elif isinstance(env_phone_numbers, EnvPhoneNumbers):
            self.env_phone_numbers = env_phone_numbers
        else:
            self.env_phone_numbers = EnvPhoneNumbers(
                sandbox=env_phone_numbers.get("sandbox", ""),
                pre_release=env_phone_numbers.get("pre_release")
                or env_phone_numbers.get("preRelease", ""),
                live=env_phone_numbers.get("live", ""),
            )

    def to_yaml_dict(self) -> dict:
        return {
            "name": self.name,
            "text": self.text,
            "env_phone_numbers": (
                self.env_phone_numbers.to_yaml_dict()
                if self.env_phone_numbers
                else {"sandbox": "", "pre_release": "", "live": ""}
            ),
        }

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join("config", "sms_templates.yaml", self.top_level_name, path_safe_name)

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        return "twilio_sms"

    @classmethod
    def from_yaml_dict(
        cls, yaml_data: dict, resource_id: str, name: str, **kwargs
    ) -> "SMSTemplate":
        return cls(
            resource_id=resource_id,
            name=yaml_data.get("name", ""),
            text=yaml_data.get("text", ""),
            env_phone_numbers=yaml_data.get("env_phone_numbers", {}),
        )

    @property
    def command_type(self) -> str:
        return "sms_template"

    @property
    def delete_command_type(self) -> str:
        return "sms_delete_template"

    @property
    def create_command_type(self) -> str:
        return "sms_create_template"

    @property
    def update_command_type(self) -> str:
        return "sms_update_template"

    def build_update_proto(self) -> SMS_UpdateTemplate:
        return SMS_UpdateTemplate(
            id=self.resource_id,
            name=self.name,
            text=self.text,
            env_phone_numbers=UpdateSMSEnvPhoneNumbers(
                sandbox=self.env_phone_numbers.sandbox,
                pre_release=self.env_phone_numbers.pre_release,
                live=self.env_phone_numbers.live,
            ),
            active=True,
        )

    def build_delete_proto(self) -> SMS_DeleteTemplate:
        return SMS_DeleteTemplate(
            id=self.resource_id,
        )

    def build_create_proto(self) -> SMS_CreateTemplate:
        return SMS_CreateTemplate(
            id=self.resource_id,
            name=self.name,
            text=self.text,
            env_phone_numbers=SMSEnvPhoneNumbers(
                sandbox=self.env_phone_numbers.sandbox,
                pre_release=self.env_phone_numbers.pre_release,
                live=self.env_phone_numbers.live,
            ),
            references=SMSTemplateReferences(
                topics={},
                flow_steps={},
                variables={},
            ),
            active=True,
        )

    def validate(self, **kwargs) -> None:
        if not self.name:
            raise ValueError("Name is required")
        if not self.text:
            raise ValueError("Text is required")
        if not self.env_phone_numbers:
            raise ValueError("Env phone numbers are required")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        sms_templates_path = os.path.join(base_path, "config", "sms_templates.yaml")
        discovered_sms_templates: list[str] = []

        if not os.path.exists(sms_templates_path):
            return discovered_sms_templates

        yaml_dict = SMSTemplate._get_top_level_data(sms_templates_path)
        sms_templates: list[dict] = yaml_dict.get("sms_templates", []) if yaml_dict else []

        for sms_template in sms_templates:
            name = sms_template.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_sms_templates.append(
                os.path.join(sms_templates_path, SMSTemplate.top_level_name, path_safe_name)
            )

        return discovered_sms_templates

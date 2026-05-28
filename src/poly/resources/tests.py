"""Handling and managing Agent Studio Tests

Copyright PolyAI Limited
"""

import os

from dataclasses import dataclass, field
from typing import Optional
from poly.resources.resource import ResourceMapping, YamlResource, SubResource
from poly.resources.variant_attributes import Variant
import poly.resources.resource_utils as utils

# import uuid
from poly.handlers.protobuf.testing_pb2 import Create_TestCase, Update_TestCase, Delete_TestCase

INTERNAL_TO_CHANNEL = {
    "chat.polyai": "voice",
    "webchat.polyai": "webchat",
}

CHANNEL_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_CHANNEL.items()}


@dataclass
class PromptCaseAssertion(SubResource):
    """Dataclass representing a Prompt Assertion"""

    pass


@dataclass
class TestCase(YamlResource):
    """Dataclass representing an Agent Studio Test"""

    name: str
    scenario: str
    channel: str
    # prompt_assertions: list[PromptAssertion] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    variant: Optional[str] = None
    language: Optional[str] = None

    @property
    def file_path(self) -> str:
        file_name = f"{utils.clean_name(self.name)}.yaml"
        return os.path.join("tests", file_name)

    def to_yaml_dict(self) -> dict:
        output = {
            "name": self.name,
            "scenario": self.scenario,
            "channel": INTERNAL_TO_CHANNEL.get(self.channel, self.channel),
            "tags": self.tags,
        }
        # if self.prompt_assertions:
        #     output["prompt_assertions"] = [assertion.name for assertion in self.prompt_assertions]
        if self.variant:
            output["variant"] = self.variant
        if self.language:
            output["language"] = self.language
        return output

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str,
        known_prompt_assertions: list[PromptCaseAssertion] = None,
        **kwargs,
    ) -> "TestCase":
        resolved_name = yaml_dict.get("name")

        # known_prompt_assertions = known_prompt_assertions or []
        # prompt_assertion_name_map = {assertion.name: assertion for assertion in known_prompt_assertions}

        # prompt_assertions = []
        # for prompt_assertion_yaml in yaml_dict.get("prompt_assertions", []):
        #     prompt_assertion = prompt_assertion_yaml.get("assertion")
        #     known_prompt_assertion = prompt_assertion_name_map.get(prompt_assertion)
        #     if known_prompt_assertion:
        #         prompt_assertions.append(known_prompt_assertion)
        #     else:
        #         prompt_assertions.append(PromptAssertion(
        #             resource_id=f"PROMPT_ASSERTION-{uuid.uuid4().hex[:8]}",
        #             name=prompt_assertion
        #         ))
        channel = yaml_dict.get("channel")
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            scenario=yaml_dict.get("scenario"),
            channel=CHANNEL_TO_INTERNAL.get(channel, channel),
            # prompt_assertions=[PromptAssertion(assertion=assertion) for assertion in yaml_dict.get("prompt_assertions", [])],
            tags=yaml_dict.get("tags", []),
            variant=yaml_dict.get("variant"),
            language=yaml_dict.get("language"),
        )

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        if variant_id := d.get("variant"):
            variant_name = next(
                (
                    resource.resource_name
                    for resource in resource_mappings or []
                    if resource.resource_id == variant_id and resource.resource_type == Variant
                ),
                variant_id,
            )
            d["variant"] = variant_name
        return d

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> dict:
        """Replace resource names with IDs in a parsed YAML dict."""
        if variant_name := yaml_dict.get("variant"):
            variant_id = next(
                (
                    resource.resource_id
                    for resource in resource_mappings or []
                    if resource.resource_name == variant_name and resource.resource_type == Variant
                ),
                variant_name,
            )
            yaml_dict["variant"] = variant_id
        return yaml_dict

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "TestCase":
        """Read a local YAML resource, validating name against filename."""
        test_case: TestCase = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )

        file_name = os.path.splitext(os.path.basename(file_path))[0]
        expected_file_name = utils.clean_name(test_case.name)

        if file_name != expected_file_name:
            raise ValueError(
                f"Test case name '{test_case.name}' in file {file_name}.yaml does not match "
                f"expected filename: {expected_file_name}.yaml"
            )
        return test_case

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        tests_path = os.path.join(base_path, "tests")
        if not os.path.exists(tests_path):
            return []
        return [
            os.path.join(tests_path, file_name)
            for file_name in os.listdir(tests_path)
            if file_name.endswith(".yaml")
        ]

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the test case resource."""
        # Channel is Voice or Webchat
        if self.channel not in INTERNAL_TO_CHANNEL:
            raise ValueError(f"Invalid channel: {self.channel}")

        # Prompt exists
        if not self.scenario:
            raise ValueError("Scenario is required")

        # Variant is valid if exists
        if self.variant:
            if not next(
                (
                    resource
                    for resource in resource_mappings or []
                    if resource.resource_id == self.variant and resource.resource_type == Variant
                ),
                None,
            ):
                raise ValueError(f"Variant {self.variant} not found")

        # TODO: Language is configured language (Once translations is merged)

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["TestCase"] = None
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Get the new, updated, and deleted subresources within this resource.

        Returns:
            tuple[
                list[SubResource],
                list[SubResource],
                list[SubResource],
            ]: A tuple containing three lists of subresources:
                - New subresources
                - Updated subresources
                - Deleted subresources
        """
        new = []
        updated = []
        deleted = []
        # old_prompt_assertion_ids = {assertion.resource_id for assertion in old_resource.prompt_assertions} if old_resource else set()
        # new_prompt_assertion_ids = {assertion.resource_id for assertion in self.prompt_assertions}

        # for prompt_assertion in self.prompt_assertions:
        #     if prompt_assertion.resource_id not in old_prompt_assertion_ids:
        #         new.append(prompt_assertion)
        #     else:
        #         # Check if updated
        #         old_prompt_assertion = next(
        #             (assertion for assertion in old_resource.prompt_assertions if assertion.resource_id == prompt_assertion.resource_id),
        #             None
        #         )
        #         if old_prompt_assertion and prompt_assertion != old_prompt_assertion:
        #             updated.append(prompt_assertion)

        # if old_resource:
        #     for prompt_assertion in old_resource.prompt_assertions:
        #         if prompt_assertion.resource_id not in new_prompt_assertion_ids:
        #             deleted.append(prompt_assertion)

        return new, updated, deleted

    @property
    def command_type(self) -> str:
        return "test_case"

    def build_create_proto(self) -> Create_TestCase:
        return Create_TestCase(
            id=self.resource_id,
            name=self.name,
            scenario=self.scenario,
            variant_id=self.variant,
            language=self.language,
            channel=self.channel,
        )

    def build_update_proto(self) -> Update_TestCase:
        return Update_TestCase(
            id=self.resource_id,
            name=self.name,
            scenario=self.scenario,
            variant_id=self.variant,
            language=self.language,
            channel=self.channel,
        )

    def build_delete_proto(self) -> Delete_TestCase:
        return Delete_TestCase(id=self.resource_id)

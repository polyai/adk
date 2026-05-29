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
from poly.handlers.protobuf.testing_pb2 import (
    Create_TestCase,
    Update_TestCase,
    Delete_TestCase,
    SetTestCaseAssertions,
    SetTestCaseTags,
    TestCaseAssertion as TestCaseAssertionProto,
    PromptAssertion,
    FunctionCallAssertion as FunctionCallAssertionProto,
    FunctionCallAssertionArgument as FunctionCallAssertionArgumentProto,
)

INTERNAL_TO_CHANNEL = {
    "chat.polyai": "voice",
    "webchat.polyai": "webchat",
}

CHANNEL_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_CHANNEL.items()}


ALLOWED_TYPES = ["string", "integer", "number", "boolean"]


@dataclass
class FunctionCallArgumentAssertion:
    parameter_name: str
    expected_value: str
    value_type: str
    assertion_type: str = "equals"

    def to_yaml_dict(self) -> dict:
        return {
            "parameter_name": self.parameter_name,
            "expected_value": self.expected_value,
            "value_type": self.value_type,
        }

    def to_proto(self) -> FunctionCallAssertionArgumentProto:
        return FunctionCallAssertionArgumentProto(
            value_type=self.value_type,
            assertion_type=self.assertion_type,
            expected_value=self.expected_value,
        )


@dataclass
class FunctionCallAssertion:
    name: str
    arguments: list[FunctionCallArgumentAssertion]

    def __init__(self, name: str, arguments: list[FunctionCallArgumentAssertion | dict]):
        self.name = name
        self.arguments = [
            FunctionCallArgumentAssertion(**argument) if isinstance(argument, dict) else argument
            for argument in arguments
        ]

    def to_yaml_dict(self) -> dict:
        return {"name": self.name, "arguments": [arg.to_yaml_dict() for arg in self.arguments]}

    def to_proto(self) -> FunctionCallAssertionProto:
        return FunctionCallAssertionProto(
            name=self.name, arguments={arg.parameter_name: arg.to_proto() for arg in self.arguments}
        )


@dataclass
class TestCaseAssertion(SubResource):
    """Dataclass representing a Prompt Assertion"""

    prompts: list[str] = field(default_factory=list)
    function_calls: list[FunctionCallAssertion] = field(default_factory=list)

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        prompts: list[str],
        function_calls: list[FunctionCallAssertion | dict],
    ):
        self.resource_id = resource_id
        self.name = name
        self.prompts = prompts
        self.function_calls = [
            FunctionCallAssertion(**function_call)
            if isinstance(function_call, dict)
            else function_call
            for function_call in function_calls
        ]

    def to_yaml_dict(self) -> dict:
        response = {}
        if self.prompts:
            response["prompt_assertions"] = self.prompts
        if self.function_calls:
            response["function_call_assertions"] = [
                function_call.to_yaml_dict() for function_call in self.function_calls
            ]
        return response

    @property
    def command_type(self) -> str:
        return "test_case_assertion"

    @property
    def update_command_type(self) -> str:
        return "set_test_case_assertions"

    def _build_assertions_proto(self) -> list[TestCaseAssertionProto]:
        assertions = []
        for prompt in self.prompts:
            assertions.append(TestCaseAssertionProto(prompt=PromptAssertion(value=prompt)))
        for function_call in self.function_calls:
            assertions.append(TestCaseAssertionProto(function_call=function_call.to_proto()))
        return assertions

    def build_update_proto(self) -> SetTestCaseAssertions:
        return SetTestCaseAssertions(
            id=self.resource_id,
            assertions=self._build_assertions_proto(),
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("Test Case Tags cannot be created")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Test Case Tags cannot be deleted")


@dataclass
class TestCaseTags(SubResource):
    """Dataclass representing a Test Case Tags"""

    tags: list[str] = field(default_factory=list)

    @property
    def command_type(self) -> str:
        return "test_case_tags"

    @property
    def update_command_type(self) -> str:
        return "set_test_case_tags"

    def build_update_proto(self) -> SetTestCaseTags:
        return SetTestCaseTags(
            id=self.resource_id,
            tags=self.tags,
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("Test Case Tags cannot be created")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Test Case Tags cannot be deleted")


@dataclass
class TestCase(YamlResource):
    """Dataclass representing an Agent Studio Test"""

    name: str
    scenario: str
    channel: str
    assertions: TestCaseAssertion = None
    tags: TestCaseTags = None
    variant: Optional[str] = None
    language: Optional[str] = None

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        scenario: str,
        channel: str,
        assertions: TestCaseAssertion | dict,
        tags: TestCaseTags | dict,
        variant: Optional[str] = None,
        language: Optional[str] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.scenario = scenario
        self.channel = channel
        if isinstance(assertions, TestCaseAssertion):
            self.assertions = assertions
        else:
            self.assertions = TestCaseAssertion(**assertions)
        if isinstance(tags, TestCaseTags):
            self.tags = tags
        else:
            self.tags = TestCaseTags(**tags)
        self.variant = variant
        self.language = language

    @property
    def file_path(self) -> str:
        file_name = f"{utils.clean_name(self.name)}.yaml"
        return os.path.join("tests", file_name)

    def to_yaml_dict(self) -> dict:
        output = {
            "name": self.name,
            "scenario": self.scenario,
            "channel": INTERNAL_TO_CHANNEL.get(self.channel, self.channel),
        }
        if self.variant:
            output["variant"] = self.variant
        if self.language:
            output["language"] = self.language

        if tags_list := self.tags.tags:
            output["tags"] = tags_list

        if assert_dict := self.assertions.to_yaml_dict():
            output.update(assert_dict)

        return output

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str,
        **kwargs,
    ) -> "TestCase":
        resolved_name = yaml_dict.get("name")

        prompts = yaml_dict.get("prompt_assertions", [])
        function_calls = yaml_dict.get("function_call_assertions", [])
        function_assertions = [
            FunctionCallAssertion(
                name=function_call.get("name"),
                arguments=function_call.get("arguments", []),
            )
            for function_call in function_calls
        ]
        test_case_assertion = TestCaseAssertion(
            resource_id=resource_id,
            name="assertions",
            prompts=prompts,
            function_calls=function_assertions,
        )

        tags = yaml_dict.get("tags", [])
        test_case_tags = TestCaseTags(resource_id=resource_id, name="tags", tags=tags)

        channel = yaml_dict.get("channel")
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            scenario=yaml_dict.get("scenario"),
            channel=CHANNEL_TO_INTERNAL.get(channel, channel),
            assertions=test_case_assertion,
            tags=test_case_tags,
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
        updated = []

        if not old_resource:
            updated.append(self.assertions)
            updated.append(self.tags)
        else:
            if old_resource.assertions != self.assertions:
                updated.append(self.assertions)
            if old_resource.tags != self.tags:
                updated.append(self.tags)

        return [], updated, []

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

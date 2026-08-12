"""Handling and managing Agent Studio Tests

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from google.protobuf.struct_pb2 import Struct

import poly.resources.resource_utils as utils

# import uuid
from poly.handlers.protobuf.testing_pb2 import (
    Create_TestCase,
    Delete_TestCase,
    PromptAssertion,
    SetTestCaseAssertions,
    SetTestCaseIntegrationAttributes,
    SetTestCaseSipHeaders,
    SetTestCaseTags,
    Update_TestCase,
)
from poly.handlers.protobuf.testing_pb2 import (
    FunctionCallAssertion as FunctionCallAssertionProto,
)
from poly.handlers.protobuf.testing_pb2 import (
    FunctionCallAssertionArgument as FunctionCallAssertionArgumentProto,
)
from poly.handlers.protobuf.testing_pb2 import (
    TestCaseAssertion as TestCaseAssertionProto,
)
from poly.resources.languages import AdditionalLanguage, DefaultLanguage
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource
from poly.resources.variant_attributes import Variant

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

    __test__ = False

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

    __test__ = False

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


def _header_value(value: Any) -> str:
    """Render a YAML value as the text a carrier would actually send.

    SIP headers are `map<string, string>`, but YAML types unquoted scalars, so
    `x-flag: true` arrives as a Python bool. Plain `str()` would send `"True"`
    — Python's capitalisation, which no carrier and no other client produces.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


@dataclass
class TestCaseSipHeaders(SubResource):
    """Dataclass representing the mock SIP headers on a test case"""

    __test__ = False

    headers: dict[str, str] = field(default_factory=dict)

    @property
    def command_type(self) -> str:
        return "test_case_sip_headers"

    @property
    def update_command_type(self) -> str:
        return "set_test_case_sip_headers"

    def build_update_proto(self) -> SetTestCaseSipHeaders:
        return SetTestCaseSipHeaders(
            id=self.resource_id,
            # map<string, string> on the wire: a header value is always text,
            # unlike an integration attribute.
            sip_headers={str(key): _header_value(value) for key, value in self.headers.items()},
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("Test Case SIP Headers cannot be created")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Test Case SIP Headers cannot be deleted")


def _normalise_attribute(value: Any) -> Any:
    """Render a value read back from a Struct the way it was written.

    `google.protobuf.Struct` holds every number as a double, so an attribute
    pushed as `2` returns as `2.0` and would be written back to YAML that way,
    producing a spurious diff on every pull after a push. Integral floats are
    folded back to int; genuine decimals are untouched.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _normalise_attribute(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_attribute(item) for item in value]
    return value


def _validate_attribute_value(value: Any, path: str) -> None:
    """Reject values a google.protobuf.Struct cannot carry.

    YAML types unquoted scalars, so `expiry: 2026-08-12` becomes a
    `datetime.date` and `Struct.update` fails with a bare
    `ValueError: Unexpected type` naming neither the key nor the file. The
    wire format is JSON, exactly as in the UI, where the type picker offers
    string, number, boolean and JSON and nothing else.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"Integration attribute key {path}.{key!r} must be text — "
                    f"quote it to stop YAML reading it as {type(key).__name__}"
                )
            _validate_attribute_value(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_attribute_value(item, f"{path}[{index}]")
        return
    if isinstance(value, (date, datetime)):
        raise ValueError(
            f"Integration attribute '{path}' is a {type(value).__name__}, which the agent "
            f"cannot receive — quote it to send it as text: '{value.isoformat()}'"
        )
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError(
            f"Integration attribute '{path}' is a {type(value).__name__}; "
            "only text, numbers, true/false, lists and nested maps are supported"
        )


@dataclass
class TestCaseIntegrationAttributes(SubResource):
    """Dataclass representing the mock integration attributes on a test case"""

    __test__ = False

    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def command_type(self) -> str:
        return "test_case_integration_attributes"

    @property
    def update_command_type(self) -> str:
        return "set_test_case_integration_attributes"

    def to_yaml_dict(self) -> dict:
        return _normalise_attribute(self.attributes)

    def build_update_proto(self) -> SetTestCaseIntegrationAttributes:
        # google.protobuf.Struct, not a string map: values keep their JSON type
        # through to conv.integration_attributes, so a flow branching on
        # `retry_count > 2` sees a number rather than "2".
        attributes = Struct()
        attributes.update(self.attributes)
        return SetTestCaseIntegrationAttributes(
            id=self.resource_id,
            integration_attributes=attributes,
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("Test Case Integration Attributes cannot be created")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Test Case Integration Attributes cannot be deleted")


@register_resource("test_cases")
@dataclass
class TestCase(YamlResource):
    """Dataclass representing an Agent Studio Test"""

    __test__ = False

    name: str
    scenario: str
    channel: str
    language: str
    assertions: TestCaseAssertion = None
    tags: TestCaseTags = None
    variant: Optional[str] = None
    caller_number: Optional[str] = None
    sip_headers: "TestCaseSipHeaders" = None
    integration_attributes: "TestCaseIntegrationAttributes" = None

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "TestCase"]:
        """Parse test cases from a projection dict."""
        test_cases = {}
        for test_case_id, test_case_data in (
            projection.get("testing", {}).get("testCases", {}).get("entities", {}).items()
        ):
            prompt_assertions = []
            function_assertions = []
            for assertion in test_case_data.get("assertions", []):
                assertion_payload = assertion.get("payload", {})
                if assertion_payload.get("$case") == "prompt":
                    prompt_assertions.append(assertion_payload.get("value").get("value"))
                elif assertion_payload.get("$case") == "functionCall":
                    assertion_value = assertion_payload.get("value", {})
                    arguments = [
                        FunctionCallArgumentAssertion(
                            parameter_name=arg,
                            expected_value=arg_values.get("expectedValue"),
                            value_type=arg_values.get("valueType"),
                        )
                        for arg, arg_values in assertion_value.get("arguments").items()
                    ]
                    function_assertions.append(
                        FunctionCallAssertion(name=assertion_value.get("name"), arguments=arguments)
                    )
            assertions = TestCaseAssertion(
                resource_id=test_case_id,
                name="assertions",
                prompts=prompt_assertions,
                function_calls=function_assertions,
            )
            tags = TestCaseTags(
                resource_id=test_case_id, name="tags", tags=test_case_data.get("tags", [])
            )
            sip_headers = TestCaseSipHeaders(
                resource_id=test_case_id,
                name="sip_headers",
                headers=test_case_data.get("sipHeaders") or {},
            )
            integration_attributes = TestCaseIntegrationAttributes(
                resource_id=test_case_id,
                name="integration_attributes",
                attributes=test_case_data.get("integrationAttributes") or {},
            )
            test_cases[test_case_id] = cls(
                resource_id=test_case_id,
                name=test_case_data.get("name", ""),
                scenario=test_case_data.get("scenario", ""),
                variant=test_case_data.get("variantId", ""),
                language=test_case_data.get("language", ""),
                channel=test_case_data.get("channel", ""),
                assertions=assertions,
                tags=tags,
                caller_number=test_case_data.get("callerNumber", ""),
                sip_headers=sip_headers,
                integration_attributes=integration_attributes,
            )
        return test_cases

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        scenario: str,
        channel: str,
        language: str,
        assertions: TestCaseAssertion | dict,
        tags: TestCaseTags | dict,
        variant: Optional[str] = None,
        caller_number: Optional[str] = None,
        sip_headers: "TestCaseSipHeaders | dict | None" = None,
        integration_attributes: "TestCaseIntegrationAttributes | dict | None" = None,
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
        self.caller_number = caller_number
        # Both are always constructed, even when empty. Clearing a value has to
        # produce a command, and get_new_updated_deleted_subresources works by
        # comparing subresources — an absent one cannot differ from anything.
        if isinstance(sip_headers, TestCaseSipHeaders):
            self.sip_headers = sip_headers
        else:
            self.sip_headers = TestCaseSipHeaders(
                resource_id=resource_id, name="sip_headers", headers=sip_headers or {}
            )
        if isinstance(integration_attributes, TestCaseIntegrationAttributes):
            self.integration_attributes = integration_attributes
        else:
            self.integration_attributes = TestCaseIntegrationAttributes(
                resource_id=resource_id,
                name="integration_attributes",
                attributes=integration_attributes or {},
            )

    @property
    def file_path(self) -> str:
        file_name = f"{utils.clean_name(self.name)}.yaml"
        return os.path.join("test_suite", file_name)

    def to_yaml_dict(self) -> dict:
        output = {
            "name": self.name,
            "scenario": self.scenario,
            "channel": INTERNAL_TO_CHANNEL.get(self.channel, self.channel),
        }
        output["language"] = self.language
        if self.variant:
            output["variant"] = self.variant

        if self.caller_number:
            output["caller_number"] = self.caller_number

        if tags_list := self.tags.tags:
            output["tags"] = tags_list

        if headers := self.sip_headers.headers:
            output["sip_headers"] = headers

        if attributes := self.integration_attributes.to_yaml_dict():
            output["integration_attributes"] = attributes

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

        test_case_sip_headers = TestCaseSipHeaders(
            resource_id=resource_id,
            name="sip_headers",
            headers=yaml_dict.get("sip_headers") or {},
        )
        test_case_integration_attributes = TestCaseIntegrationAttributes(
            resource_id=resource_id,
            name="integration_attributes",
            attributes=yaml_dict.get("integration_attributes") or {},
        )

        channel = yaml_dict.get("channel")
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            scenario=yaml_dict.get("scenario"),
            channel=CHANNEL_TO_INTERNAL.get(channel, channel),
            language=yaml_dict.get("language", ""),
            assertions=test_case_assertion,
            tags=test_case_tags,
            variant=yaml_dict.get("variant"),
            caller_number=yaml_dict.get("caller_number"),
            sip_headers=test_case_sip_headers,
            integration_attributes=test_case_integration_attributes,
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
        yaml_dict = super().from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, **kwargs
        )
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
        tests_path = os.path.join(base_path, "test_suite")
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

        if not self.language:
            raise ValueError("Language is required")

        configured_languages = {
            m.resource_name
            for m in resource_mappings or []
            if m.resource_type in (DefaultLanguage, AdditionalLanguage)
        }
        if configured_languages and self.language not in configured_languages:
            raise ValueError(
                f"Language '{self.language}' is not configured. "
                f"Available languages: {sorted(configured_languages)}"
            )

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

        # Integration attributes carry JSON types through to the agent
        _validate_attribute_value(self.integration_attributes.attributes, "integration_attributes")

        # Function name is valid
        known_global_functions = {
            resource.resource_name
            for resource in resource_mappings or []
            if resource.resource_prefix == "fn"
        }
        for function_call in self.assertions.function_calls:
            if not function_call.name:
                raise ValueError("Function call assertion must have a name")
            if known_global_functions and function_call.name not in known_global_functions:
                raise ValueError(f"Unknown function in assertion: {function_call.name}")
            for argument in function_call.arguments:
                if argument.value_type not in ALLOWED_TYPES:
                    raise ValueError(
                        f"Invalid value type for function call assertion argument: {argument.value_type}"
                    )

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
            if self.sip_headers.headers:
                updated.append(self.sip_headers)
            if self.integration_attributes.attributes:
                updated.append(self.integration_attributes)
        else:
            if old_resource.assertions != self.assertions:
                updated.append(self.assertions)
            if old_resource.tags != self.tags:
                updated.append(self.tags)
            # Compared even when now empty, so clearing them pushes a command.
            if old_resource.sip_headers != self.sip_headers:
                updated.append(self.sip_headers)
            if old_resource.integration_attributes != self.integration_attributes:
                updated.append(self.integration_attributes)

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
            caller_number=self.caller_number or "",
        )

    def build_update_proto(self) -> Update_TestCase:
        return Update_TestCase(
            id=self.resource_id,
            name=self.name,
            scenario=self.scenario,
            variant_id=self.variant or "",
            language=self.language,
            channel=self.channel,
            caller_number=self.caller_number or "",
        )

    def build_delete_proto(self) -> Delete_TestCase:
        return Delete_TestCase(id=self.resource_id)

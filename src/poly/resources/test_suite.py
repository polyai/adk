"""Handling and managing Agent Studio Tests

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

from google.protobuf.struct_pb2 import Struct, Value

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.testing_pb2 import (
    ApiResponse as ApiResponseProto,
)
from poly.handlers.protobuf.testing_pb2 import (
    ApiResponseRule as ApiResponseRuleProto,
)

# import uuid
from poly.handlers.protobuf.testing_pb2 import (
    Create_TestCase,
    Delete_TestCase,
    DeleteTestCaseApiOperationMock,
    PromptAssertion,
    SetTestCaseAssertions,
    SetTestCaseIntegrationAttributes,
    SetTestCaseSipHeaders,
    SetTestCaseTags,
    Update_TestCase,
    UpdateTestCaseApiOperationMock,
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
from poly.resources.api_integration import ApiIntegration
from poly.resources.languages import AdditionalLanguage, DefaultLanguage
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource
from poly.resources.variant_attributes import Variant

logger = logging.getLogger(__name__)

INTERNAL_TO_CHANNEL = {
    "chat.polyai": "voice",
    "webchat.polyai": "webchat",
}

CHANNEL_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_CHANNEL.items()}


ALLOWED_TYPES = ["string", "integer", "number", "boolean"]

SIMULATED_AT_HINT = "an ISO 8601 datetime, e.g. 2026-01-15T09:30:00Z"


def parse_simulated_at(value: str | datetime | None) -> Optional[datetime]:
    """Parse a test clock value into a UTC datetime, or None when unset.

    Accepts an ISO 8601 string (the platform projection format) or a datetime
    (ruamel parses unquoted YAML timestamps into one). Naive datetimes are
    assumed to be UTC.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                f"Invalid simulated_at value '{value}'. Expected {SIMULATED_AT_HINT}"
            ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_simulated_at(value: Optional[datetime]) -> Optional[str]:
    """Render a test clock datetime as a canonical UTC ISO 8601 string."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


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
        return {
            "name": self.name,
            "arguments": [
                arg.to_yaml_dict()
                for arg in sorted(self.arguments, key=lambda arg: arg.parameter_name)
            ],
        }

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
                function_call.to_yaml_dict()
                for function_call in sorted(self.function_calls, key=lambda call: call.name)
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


def _python_to_value(data: Any) -> Value:
    """Convert an arbitrary JSON-compatible python value into a google.protobuf.Value.

    `Struct.__setitem__` already knows how to encode any JSON-compatible python
    value (including nested dicts/lists) into a Value — wrapping it in a
    throwaway Struct reuses that instead of hand-rolling the encoding.
    """
    wrapper = Struct()
    wrapper["value"] = data
    value = Value()
    value.CopyFrom(wrapper.fields["value"])
    return value


@dataclass
class ApiResponse:
    """A single mocked API response: status, body, and headers."""

    status: int = 200
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_yaml_dict(self) -> dict:
        response: dict[str, Any] = {"status": self.status}
        if self.body is not None:
            response["body"] = self.body
        if self.headers:
            response["headers"] = self.headers
        return response

    def to_proto(self) -> ApiResponseProto:
        kwargs: dict[str, Any] = {
            "status": self.status,
            "headers": {str(key): _header_value(value) for key, value in self.headers.items()},
        }
        if self.body is not None:
            kwargs["body"] = _python_to_value(self.body)
        return ApiResponseProto(**kwargs)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApiResponse":
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"'respond' must be a mapping with 'status' (and optional 'body'/'headers'), "
                f"got {type(data).__name__}: {data!r}"
            )
        headers = data.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError(
                f"'respond.headers' must be a mapping of header name to value, "
                f"got {type(headers).__name__}: {headers!r}"
            )
        # Mirrors _normalise_attribute: a body pushed through google.protobuf.Value
        # (a double) reads a pushed int back as a float, producing a spurious
        # diff on the next pull. Folding integral floats back to int here
        # keeps a pull-after-push round trip stable.
        return cls(
            status=data.get("status", 200),
            body=_normalise_attribute(data.get("body")),
            headers=dict(headers),
        )


@dataclass
class ApiResponseRule:
    """One rule in a mocked operation's response sequence.

    `repeat` mirrors the platform's semantics: unset means respond once, then
    advance to the next rule. `-1` means respond forever with this rule and is
    only valid on the last rule in the list. `0` and other negative values are
    rejected.
    """

    respond: ApiResponse = field(default_factory=ApiResponse)
    repeat: Optional[int] = None

    def to_yaml_dict(self) -> dict:
        response = {"respond": self.respond.to_yaml_dict()}
        if self.repeat is not None:
            response["repeat"] = self.repeat
        return response

    def to_proto(self) -> ApiResponseRuleProto:
        kwargs: dict[str, Any] = {"respond": self.respond.to_proto()}
        if self.repeat is not None:
            kwargs["repeat"] = self.repeat
        return ApiResponseRuleProto(**kwargs)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApiResponseRule":
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Response rule must be a mapping with 'respond' (and optional 'repeat'), "
                f"got {type(data).__name__}: {data!r}"
            )
        return cls(respond=ApiResponse.from_dict(data.get("respond")), repeat=data.get("repeat"))


@dataclass
class TestCaseApiMocks:
    """Container for the mocked API responses on a test case.

    Keyed by integration name, then operation name, matching how the platform
    references integrations/operations elsewhere and cascades renames/deletes
    from the api-integrations domain into existing mocks. Not itself pushed —
    each (integration, operation) pair is diffed and pushed independently as
    a `TestCaseApiOperationMock`, mirroring `ApiIntegrationEnvironments`.
    """

    __test__ = False

    mocks: dict[str, dict[str, list[ApiResponseRule]]] = field(default_factory=dict)

    def to_yaml_dict(self) -> dict:
        # Integration and operation names are sorted so pulls produce stable YAML; the
        # rules within an operation are a sequence (see `repeat`) and keep their order.
        return {
            integration_name: {
                operation_name: [
                    rule.to_yaml_dict() for rule in self.mocks[integration_name][operation_name]
                ]
                for operation_name in sorted(self.mocks[integration_name])
            }
            for integration_name in sorted(self.mocks)
        }

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, list[dict]]] | None) -> "TestCaseApiMocks":
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"api_mocks must be a mapping of integration name to operations, "
                f"got {type(data).__name__}: {data!r}"
            )
        mocks: dict[str, dict[str, list[ApiResponseRule]]] = {}
        for integration_name, operations in data.items():
            operations = operations or {}
            if not isinstance(operations, dict):
                raise ValueError(
                    f"api_mocks.{integration_name} must be a mapping of operation name to a "
                    f"list of response rules, got {type(operations).__name__}: {operations!r}"
                )
            mocks[integration_name] = {}
            for operation_name, rules in operations.items():
                rules = rules or []
                if not isinstance(rules, list):
                    raise ValueError(
                        f"api_mocks.{integration_name}.{operation_name} must be a list of "
                        f"response rules, got {type(rules).__name__}: {rules!r}"
                    )
                parsed_rules = []
                for index, rule in enumerate(rules):
                    try:
                        parsed_rules.append(ApiResponseRule.from_dict(rule))
                    except ValueError as exc:
                        raise ValueError(
                            f"api_mocks.{integration_name}.{operation_name}[{index}]: {exc}"
                        ) from exc
                mocks[integration_name][operation_name] = parsed_rules
        return cls(mocks=mocks)

    def validate(self, known_integrations: set[str]) -> None:
        """Validate the mocked API responses.

        `known_integrations` is empty when the project's integrations aren't known
        (e.g. no resource_mappings passed in), in which case the integration-name
        check is skipped rather than rejecting everything.

        Operations aren't tracked as standalone resources, so operation names are
        trusted here the same way the platform trusts them when cascading renames.
        """
        for integration_name, operations in self.mocks.items():
            if not integration_name:
                raise ValueError("API mock integration name cannot be empty.")
            if known_integrations and integration_name not in known_integrations:
                raise ValueError(f"Unknown API integration in mocks: '{integration_name}'.")
            for operation_name, rules in operations.items():
                if not operation_name:
                    raise ValueError(
                        f"API mock for integration '{integration_name}' has an empty "
                        "operation name."
                    )
                if not rules:
                    raise ValueError(
                        f"API mock '{integration_name}.{operation_name}' must have at least "
                        "one response rule."
                    )
                for index, rule in enumerate(rules):
                    label = f"API mock '{integration_name}.{operation_name}'[{index}]"
                    status = rule.respond.status
                    if (
                        not isinstance(status, int)
                        or isinstance(status, bool)
                        or not (100 <= status <= 599)
                    ):
                        raise ValueError(
                            f"{label}: status '{status}' must be an HTTP status code (100-599)."
                        )
                    if rule.respond.body is not None:
                        _validate_attribute_value(rule.respond.body, f"{label}.body")
                    for header_key in rule.respond.headers:
                        if not isinstance(header_key, str) or not header_key:
                            raise ValueError(f"{label}: header keys must be non-empty text.")
                    if rule.repeat is not None:
                        if (
                            not isinstance(rule.repeat, int)
                            or isinstance(rule.repeat, bool)
                            or rule.repeat == 0
                            or rule.repeat < -1
                        ):
                            raise ValueError(
                                f"{label}: repeat '{rule.repeat}' must be a positive integer or -1."
                            )
                        if rule.repeat == -1 and index != len(rules) - 1:
                            raise ValueError(
                                f"{label}: repeat=-1 (respond forever) is only valid on the "
                                "last response rule for an operation."
                            )


@dataclass
class TestCaseApiOperationMock(SubResource):
    """One (integration, operation) pair's mocked response rules on a test case.

    The backend has no "set the whole api_mocks map" command — each operation's
    rule list is created/updated/deleted independently, so this is pushed as its
    own SubResource per pair, matching how `ApiIntegrationConfig` is pushed per
    environment rather than `ApiIntegration` pushing its environments in one shot.
    """

    __test__ = False

    resource_id: str = ""
    name: str = ""
    integration_name: str = ""
    operation_name: str = ""
    rules: list[ApiResponseRule] = field(default_factory=list)
    test_case_id: str = ""  # Set by parent when yielding from get_new_updated_deleted_subresources

    @property
    def command_type(self) -> str:
        return "test_case_api_operation_mock"

    def build_update_proto(self) -> UpdateTestCaseApiOperationMock:
        return UpdateTestCaseApiOperationMock(
            id=self.test_case_id,
            integration_name=self.integration_name,
            operation_name=self.operation_name,
            responses=[rule.to_proto() for rule in self.rules],
        )

    def build_delete_proto(self) -> DeleteTestCaseApiOperationMock:
        return DeleteTestCaseApiOperationMock(
            id=self.test_case_id,
            integration_name=self.integration_name,
            operation_name=self.operation_name,
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("Test Case API Operation Mock cannot be created independently.")


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
    simulated_at: Optional[str] = None
    sip_headers: "TestCaseSipHeaders" = None
    integration_attributes: "TestCaseIntegrationAttributes" = None
    api_mocks: "TestCaseApiMocks" = None

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "TestCase"]:
        """Parse test cases from a projection dict."""
        test_cases = {}
        test_cases_projection = (
            projection.get("testing", {}).get("testCases", {}).get("entities", {})
        )
        if "testing" not in projection or any(
            "scenario" not in tc for tc in test_cases_projection.values()
        ):
            logger.debug("No read access to test cases - they will not be pulled.")
            return {}

        for test_case_id, test_case_data in test_cases_projection.items():
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
            # The projection's apiMocks is already flat — {integration: {operation:
            # [rule, ...]}} — matching TestCaseApiMocks.from_dict directly. The
            # integrations/operations/responses wrapper is only the protobuf wire
            # shape used internally between agent-stream's backend and its own
            # store; it never reaches the projection.
            api_mocks = TestCaseApiMocks.from_dict(test_case_data.get("apiMocks"))
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
                simulated_at=test_case_data.get("simulatedAt"),
                sip_headers=sip_headers,
                integration_attributes=integration_attributes,
                api_mocks=api_mocks,
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
        simulated_at: str | datetime | None = None,
        sip_headers: "TestCaseSipHeaders | dict | None" = None,
        integration_attributes: "TestCaseIntegrationAttributes | dict | None" = None,
        api_mocks: "TestCaseApiMocks | dict | None" = None,
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
        # Trimmed on the way in, matching the platform entity: a stray trailing
        # space is invisible in a YAML file but changes the agent-memory
        # identifier the number resolves to.
        self.caller_number = (
            caller_number.strip() if isinstance(caller_number, str) else caller_number
        )
        self.simulated_at = format_simulated_at(parse_simulated_at(simulated_at))
        # Both are always constructed, even when empty. Clearing a value has to
        # produce a command, and get_new_updated_deleted_subresources works by
        # comparing subresources — an absent one cannot differ from anything.
        if isinstance(sip_headers, TestCaseSipHeaders):
            self.sip_headers = sip_headers
        elif sip_headers:
            self.sip_headers = TestCaseSipHeaders(**sip_headers)
        else:
            self.sip_headers = TestCaseSipHeaders(resource_id=resource_id, name="sip_headers")
        if isinstance(integration_attributes, TestCaseIntegrationAttributes):
            self.integration_attributes = integration_attributes
        elif integration_attributes:
            self.integration_attributes = TestCaseIntegrationAttributes(**integration_attributes)
        else:
            self.integration_attributes = TestCaseIntegrationAttributes(
                resource_id=resource_id, name="integration_attributes"
            )
        if isinstance(api_mocks, TestCaseApiMocks):
            self.api_mocks = api_mocks
        elif api_mocks:
            # resource_to_dict wraps a plain dataclass's field under its own name,
            # unlike a SubResource — so a status-file dict here is {"mocks": {...}}.
            self.api_mocks = TestCaseApiMocks.from_dict(api_mocks.get("mocks", api_mocks))
        else:
            self.api_mocks = TestCaseApiMocks()

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

        if self.simulated_at:
            output["simulated_at"] = self.simulated_at

        if tags_list := self.tags.tags:
            output["tags"] = tags_list

        if headers := self.sip_headers.headers:
            output["sip_headers"] = headers

        if attributes := self.integration_attributes.to_yaml_dict():
            output["integration_attributes"] = attributes

        if mocks := self.api_mocks.to_yaml_dict():
            output["api_mocks"] = mocks

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
        test_case_api_mocks = TestCaseApiMocks.from_dict(yaml_dict.get("api_mocks"))

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
            simulated_at=yaml_dict.get("simulated_at"),
            sip_headers=test_case_sip_headers,
            integration_attributes=test_case_integration_attributes,
            api_mocks=test_case_api_mocks,
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

        # An unquoted number is the easy mistake here, and a silent one: YAML
        # reads `+447700900000` as the int 447700900000, dropping the leading
        # `+`. Coercing it back to text would send a different number, so this
        # rejects rather than guesses.
        if self.caller_number is not None and not isinstance(self.caller_number, str):
            raise ValueError(
                f"caller_number must be text, got {type(self.caller_number).__name__} "
                f"({self.caller_number}) — quote it so YAML keeps it as written, "
                "including any leading '+' or zeros"
            )

        # Integration attributes carry JSON types through to the agent
        _validate_attribute_value(self.integration_attributes.attributes, "integration_attributes")

        # API mocks: integration must exist (when the project's integrations are known).
        known_integrations = {
            m.resource_name for m in resource_mappings or [] if m.resource_type is ApiIntegration
        }
        self.api_mocks.validate(known_integrations)

        # `fn` is a global function, `ft` a flow function. Both are assertable.
        known_functions = {
            resource.resource_name
            for resource in resource_mappings or []
            if resource.resource_prefix in ("fn", "ft")
        }
        for function_call in self.assertions.function_calls:
            if not function_call.name:
                raise ValueError("Function call assertion must have a name")
            if known_functions and function_call.name not in known_functions:
                raise ValueError(f"Unknown function in assertion: {function_call.name}")
            for argument in function_call.arguments:
                if argument.value_type not in ALLOWED_TYPES:
                    raise ValueError(
                        f"Invalid value type for function call assertion argument: {argument.value_type}"
                    )

    def _diff_api_mocks(
        self, old_mocks: dict[str, dict[str, list[ApiResponseRule]]]
    ) -> tuple[list[SubResource], list[SubResource]]:
        """Diff api_mocks against `old_mocks`, one (integration, operation) pair at a time.

        There's no "set the whole map" command for api_mocks (unlike sip_headers/
        integration_attributes), so each changed or new pair becomes its own update,
        and each pair present in `old_mocks` but gone from `self.api_mocks.mocks`
        becomes its own delete.
        """
        updated: list[SubResource] = []
        seen_pairs: set[tuple[str, str]] = set()

        for integration_name, operations in self.api_mocks.mocks.items():
            for operation_name, rules in operations.items():
                seen_pairs.add((integration_name, operation_name))
                old_rules = old_mocks.get(integration_name, {}).get(operation_name)
                if old_rules != rules:
                    updated.append(
                        TestCaseApiOperationMock(
                            resource_id=f"{self.resource_id}:{integration_name}:{operation_name}",
                            name="api_mocks",
                            integration_name=integration_name,
                            operation_name=operation_name,
                            rules=rules,
                            test_case_id=self.resource_id,
                        )
                    )

        deleted: list[SubResource] = [
            TestCaseApiOperationMock(
                resource_id=f"{self.resource_id}:{integration_name}:{operation_name}",
                name="api_mocks",
                integration_name=integration_name,
                operation_name=operation_name,
                test_case_id=self.resource_id,
            )
            for integration_name, operations in old_mocks.items()
            for operation_name in operations
            if (integration_name, operation_name) not in seen_pairs
        ]

        return updated, deleted

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
        deleted = []

        if not old_resource:
            updated.append(self.assertions)
            updated.append(self.tags)
            if self.sip_headers.headers:
                updated.append(self.sip_headers)
            if self.integration_attributes.attributes:
                updated.append(self.integration_attributes)
            mock_updates, mock_deletes = self._diff_api_mocks({})
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
            mock_updates, mock_deletes = self._diff_api_mocks(old_resource.api_mocks.mocks)

        updated.extend(mock_updates)
        deleted.extend(mock_deletes)

        return [], updated, deleted

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
            # Empty string is the explicit "clear" signal, as for caller_number and
            # variant_id — an omitted optional field reads as "no update" platform-side.
            simulated_at=self.simulated_at or "",
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
            # Empty string is the explicit "clear" signal, as for caller_number and
            # variant_id — an omitted optional field reads as "no update" platform-side.
            simulated_at=self.simulated_at or "",
        )

    def build_delete_proto(self) -> Delete_TestCase:
        return Delete_TestCase(id=self.resource_id)

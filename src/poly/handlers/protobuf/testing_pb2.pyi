from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Testing(_message.Message):
    __slots__ = ("test_cases",)
    TEST_CASES_FIELD_NUMBER: _ClassVar[int]
    test_cases: _containers.RepeatedCompositeFieldContainer[TestCase]
    def __init__(self, test_cases: _Optional[_Iterable[_Union[TestCase, _Mapping]]] = ...) -> None: ...

class FunctionCallAssertionArgument(_message.Message):
    __slots__ = ("value_type", "assertion_type", "expected_value")
    VALUE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ASSERTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VALUE_FIELD_NUMBER: _ClassVar[int]
    value_type: str
    assertion_type: str
    expected_value: str
    def __init__(self, value_type: _Optional[str] = ..., assertion_type: _Optional[str] = ..., expected_value: _Optional[str] = ...) -> None: ...

class FunctionCallAssertion(_message.Message):
    __slots__ = ("name", "arguments", "is_asserted")
    class ArgumentsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: FunctionCallAssertionArgument
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[FunctionCallAssertionArgument, _Mapping]] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    IS_ASSERTED_FIELD_NUMBER: _ClassVar[int]
    name: str
    arguments: _containers.MessageMap[str, FunctionCallAssertionArgument]
    is_asserted: bool
    def __init__(self, name: _Optional[str] = ..., arguments: _Optional[_Mapping[str, FunctionCallAssertionArgument]] = ..., is_asserted: bool = ...) -> None: ...

class PromptAssertion(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: str
    def __init__(self, value: _Optional[str] = ...) -> None: ...

class TestCaseAssertion(_message.Message):
    __slots__ = ("prompt", "function_call")
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_CALL_FIELD_NUMBER: _ClassVar[int]
    prompt: PromptAssertion
    function_call: FunctionCallAssertion
    def __init__(self, prompt: _Optional[_Union[PromptAssertion, _Mapping]] = ..., function_call: _Optional[_Union[FunctionCallAssertion, _Mapping]] = ...) -> None: ...

class ApiResponse(_message.Message):
    __slots__ = ("status", "body", "headers")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    STATUS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    status: int
    body: _struct_pb2.Value
    headers: _containers.ScalarMap[str, str]
    def __init__(self, status: _Optional[int] = ..., body: _Optional[_Union[_struct_pb2.Value, _Mapping]] = ..., headers: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ApiResponseRule(_message.Message):
    __slots__ = ("respond", "repeat")
    RESPOND_FIELD_NUMBER: _ClassVar[int]
    REPEAT_FIELD_NUMBER: _ClassVar[int]
    respond: ApiResponse
    repeat: int
    def __init__(self, respond: _Optional[_Union[ApiResponse, _Mapping]] = ..., repeat: _Optional[int] = ...) -> None: ...

class ApiResponseRuleList(_message.Message):
    __slots__ = ("responses",)
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[ApiResponseRule]
    def __init__(self, responses: _Optional[_Iterable[_Union[ApiResponseRule, _Mapping]]] = ...) -> None: ...

class ApiIntegrationOverride(_message.Message):
    __slots__ = ("operations",)
    class OperationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ApiResponseRuleList
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ApiResponseRuleList, _Mapping]] = ...) -> None: ...
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    operations: _containers.MessageMap[str, ApiResponseRuleList]
    def __init__(self, operations: _Optional[_Mapping[str, ApiResponseRuleList]] = ...) -> None: ...

class ApiOverride(_message.Message):
    __slots__ = ("integrations",)
    class IntegrationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ApiIntegrationOverride
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ApiIntegrationOverride, _Mapping]] = ...) -> None: ...
    INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    integrations: _containers.MessageMap[str, ApiIntegrationOverride]
    def __init__(self, integrations: _Optional[_Mapping[str, ApiIntegrationOverride]] = ...) -> None: ...

class TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "created_by", "created_at", "updated_by", "updated_at", "tags", "simulated_at", "assertions", "channel", "severity", "api_mocks", "caller_number", "sip_headers", "integration_attributes")
    class SipHeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    ASSERTIONS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    API_MOCKS_FIELD_NUMBER: _ClassVar[int]
    CALLER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    scenario: str
    variant_id: str
    language: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    tags: _containers.RepeatedScalarFieldContainer[str]
    simulated_at: _timestamp_pb2.Timestamp
    assertions: _containers.RepeatedCompositeFieldContainer[TestCaseAssertion]
    channel: str
    severity: str
    api_mocks: ApiOverride
    caller_number: str
    sip_headers: _containers.ScalarMap[str, str]
    integration_attributes: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tags: _Optional[_Iterable[str]] = ..., simulated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., assertions: _Optional[_Iterable[_Union[TestCaseAssertion, _Mapping]]] = ..., channel: _Optional[str] = ..., severity: _Optional[str] = ..., api_mocks: _Optional[_Union[ApiOverride, _Mapping]] = ..., caller_number: _Optional[str] = ..., sip_headers: _Optional[_Mapping[str, str]] = ..., integration_attributes: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Create_TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "simulated_at", "channel", "caller_number")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    CALLER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    scenario: str
    variant_id: str
    language: str
    simulated_at: str
    channel: str
    caller_number: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., simulated_at: _Optional[str] = ..., channel: _Optional[str] = ..., caller_number: _Optional[str] = ...) -> None: ...

class Update_TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "simulated_at", "channel", "caller_number")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    CALLER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    scenario: str
    variant_id: str
    language: str
    simulated_at: str
    channel: str
    caller_number: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., simulated_at: _Optional[str] = ..., channel: _Optional[str] = ..., caller_number: _Optional[str] = ...) -> None: ...

class Delete_TestCase(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class SetTestCaseAssertions(_message.Message):
    __slots__ = ("id", "assertions")
    ID_FIELD_NUMBER: _ClassVar[int]
    ASSERTIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    assertions: _containers.RepeatedCompositeFieldContainer[TestCaseAssertion]
    def __init__(self, id: _Optional[str] = ..., assertions: _Optional[_Iterable[_Union[TestCaseAssertion, _Mapping]]] = ...) -> None: ...

class SetTestCaseTags(_message.Message):
    __slots__ = ("id", "tags")
    ID_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    id: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class SetTestCaseSeverity(_message.Message):
    __slots__ = ("id", "severity")
    ID_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    id: str
    severity: str
    def __init__(self, id: _Optional[str] = ..., severity: _Optional[str] = ...) -> None: ...

class UpdateTestCaseApiOperationMock(_message.Message):
    __slots__ = ("id", "integration_name", "operation_name", "responses")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_NAME_FIELD_NUMBER: _ClassVar[int]
    OPERATION_NAME_FIELD_NUMBER: _ClassVar[int]
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    id: str
    integration_name: str
    operation_name: str
    responses: _containers.RepeatedCompositeFieldContainer[ApiResponseRule]
    def __init__(self, id: _Optional[str] = ..., integration_name: _Optional[str] = ..., operation_name: _Optional[str] = ..., responses: _Optional[_Iterable[_Union[ApiResponseRule, _Mapping]]] = ...) -> None: ...

class DeleteTestCaseApiOperationMock(_message.Message):
    __slots__ = ("id", "integration_name", "operation_name")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_NAME_FIELD_NUMBER: _ClassVar[int]
    OPERATION_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    integration_name: str
    operation_name: str
    def __init__(self, id: _Optional[str] = ..., integration_name: _Optional[str] = ..., operation_name: _Optional[str] = ...) -> None: ...

class SetTestCaseSipHeaders(_message.Message):
    __slots__ = ("id", "sip_headers")
    class SipHeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    sip_headers: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[str] = ..., sip_headers: _Optional[_Mapping[str, str]] = ...) -> None: ...

class SetTestCaseIntegrationAttributes(_message.Message):
    __slots__ = ("id", "integration_attributes")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    id: str
    integration_attributes: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., integration_attributes: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

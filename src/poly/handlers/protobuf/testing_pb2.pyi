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

class TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "created_by", "created_at", "updated_by", "updated_at", "tags", "simulated_at", "assertions", "channel")
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
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tags: _Optional[_Iterable[str]] = ..., simulated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., assertions: _Optional[_Iterable[_Union[TestCaseAssertion, _Mapping]]] = ..., channel: _Optional[str] = ...) -> None: ...

class Create_TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "simulated_at", "channel")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    scenario: str
    variant_id: str
    language: str
    simulated_at: _timestamp_pb2.Timestamp
    channel: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., simulated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., channel: _Optional[str] = ...) -> None: ...

class Update_TestCase(_message.Message):
    __slots__ = ("id", "name", "scenario", "variant_id", "language", "simulated_at", "channel")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    scenario: str
    variant_id: str
    language: str
    simulated_at: _timestamp_pb2.Timestamp
    channel: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., scenario: _Optional[str] = ..., variant_id: _Optional[str] = ..., language: _Optional[str] = ..., simulated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., channel: _Optional[str] = ...) -> None: ...

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

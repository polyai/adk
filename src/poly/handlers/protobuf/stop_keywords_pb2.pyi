from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StopKeywordReferences(_message.Message):
    __slots__ = ("globalFunctions",)
    class GlobalFunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    GLOBALFUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    globalFunctions: _containers.ScalarMap[str, bool]
    def __init__(self, globalFunctions: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class RegularExpressions(_message.Message):
    __slots__ = ("patterns",)
    PATTERNS_FIELD_NUMBER: _ClassVar[int]
    patterns: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, patterns: _Optional[_Iterable[str]] = ...) -> None: ...

class StopKeywords(_message.Message):
    __slots__ = ("filters",)
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    filters: _containers.RepeatedCompositeFieldContainer[StopKeyword]
    def __init__(self, filters: _Optional[_Iterable[_Union[StopKeyword, _Mapping]]] = ...) -> None: ...

class StopKeyword(_message.Message):
    __slots__ = ("id", "title", "description", "regular_expressions", "say_phrase", "references", "created_by", "created_at", "updated_by", "updated_at", "language_code")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    SAY_PHRASE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    description: str
    regular_expressions: _containers.RepeatedScalarFieldContainer[str]
    say_phrase: bool
    references: StopKeywordReferences
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    language_code: str
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[str]] = ..., say_phrase: bool = ..., references: _Optional[_Union[StopKeywordReferences, _Mapping]] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class StopKeyword_Create(_message.Message):
    __slots__ = ("id", "title", "description", "regular_expressions", "say_phrase", "references", "language_code")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    SAY_PHRASE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    description: str
    regular_expressions: _containers.RepeatedScalarFieldContainer[str]
    say_phrase: bool
    references: StopKeywordReferences
    language_code: str
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[str]] = ..., say_phrase: bool = ..., references: _Optional[_Union[StopKeywordReferences, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class StopKeyword_Update(_message.Message):
    __slots__ = ("id", "title", "description", "regular_expressions", "say_phrase", "references", "language_code")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    SAY_PHRASE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    description: str
    regular_expressions: _containers.RepeatedScalarFieldContainer[str]
    say_phrase: bool
    references: StopKeywordReferences
    language_code: str
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[str]] = ..., say_phrase: bool = ..., references: _Optional[_Union[StopKeywordReferences, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class StopKeyword_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

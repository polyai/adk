from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WebchatCSATQuestion(_message.Message):
    __slots__ = ("id", "text", "created_at", "created_by", "updated_at", "updated_by")
    class TextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    text: _containers.ScalarMap[str, str]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., text: _Optional[_Mapping[str, str]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class WebchatCSATConfig(_message.Message):
    __slots__ = ("enabled", "survey_after_handoff", "title", "questions", "created_at", "created_by", "updated_at", "updated_by")
    class TitleEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    SURVEY_AFTER_HANDOFF_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    QUESTIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    survey_after_handoff: bool
    title: _containers.ScalarMap[str, str]
    questions: _containers.RepeatedCompositeFieldContainer[WebchatCSATQuestion]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, enabled: bool = ..., survey_after_handoff: bool = ..., title: _Optional[_Mapping[str, str]] = ..., questions: _Optional[_Iterable[_Union[WebchatCSATQuestion, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class WebchatCSAT_UpdateConfig(_message.Message):
    __slots__ = ("enabled", "survey_after_handoff")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    SURVEY_AFTER_HANDOFF_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    survey_after_handoff: bool
    def __init__(self, enabled: bool = ..., survey_after_handoff: bool = ...) -> None: ...

class WebchatCSAT_SetTitle(_message.Message):
    __slots__ = ("locale", "text")
    LOCALE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    locale: str
    text: str
    def __init__(self, locale: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class WebchatCSAT_CreateQuestion(_message.Message):
    __slots__ = ("id", "text")
    class TextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: str
    text: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[str] = ..., text: _Optional[_Mapping[str, str]] = ...) -> None: ...

class WebchatCSAT_UpdateQuestion(_message.Message):
    __slots__ = ("id", "locale", "text")
    ID_FIELD_NUMBER: _ClassVar[int]
    LOCALE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: str
    locale: str
    text: str
    def __init__(self, id: _Optional[str] = ..., locale: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class WebchatCSAT_DeleteQuestion(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

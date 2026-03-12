from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Language(_message.Message):
    __slots__ = ("code", "created_at", "created_by", "updated_at", "updated_by")
    CODE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    code: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, code: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Languages(_message.Message):
    __slots__ = ("default_language_code", "updated_by", "updated_at", "additional_languages")
    DEFAULT_LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    default_language_code: str
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    additional_languages: _containers.RepeatedCompositeFieldContainer[Language]
    def __init__(self, default_language_code: _Optional[str] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., additional_languages: _Optional[_Iterable[_Union[Language, _Mapping]]] = ...) -> None: ...

class Languages_UpdateDefaultLanguage(_message.Message):
    __slots__ = ("language_code",)
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    def __init__(self, language_code: _Optional[str] = ...) -> None: ...

class Languages_AddLanguage(_message.Message):
    __slots__ = ("code",)
    CODE_FIELD_NUMBER: _ClassVar[int]
    code: str
    def __init__(self, code: _Optional[str] = ...) -> None: ...

class Languages_DeleteLanguage(_message.Message):
    __slots__ = ("code",)
    CODE_FIELD_NUMBER: _ClassVar[int]
    code: str
    def __init__(self, code: _Optional[str] = ...) -> None: ...

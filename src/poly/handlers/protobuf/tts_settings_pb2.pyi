from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TTSSettings(_message.Message):
    __slots__ = ("language_code", "updated_by", "updated_at")
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, language_code: _Optional[str] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class TTSSettings_UpdateTTSSettings(_message.Message):
    __slots__ = ("language_code",)
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    def __init__(self, language_code: _Optional[str] = ...) -> None: ...

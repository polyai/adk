from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CSATConfig(_message.Message):
    __slots__ = ("enabled", "lead_in_message", "survey_question", "created_at", "created_by", "updated_at", "updated_by")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    LEAD_IN_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SURVEY_QUESTION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    lead_in_message: str
    survey_question: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, enabled: bool = ..., lead_in_message: _Optional[str] = ..., survey_question: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class CSAT_UpdateConfig(_message.Message):
    __slots__ = ("enabled", "lead_in_message", "survey_question")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    LEAD_IN_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SURVEY_QUESTION_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    lead_in_message: str
    survey_question: str
    def __init__(self, enabled: bool = ..., lead_in_message: _Optional[str] = ..., survey_question: _Optional[str] = ...) -> None: ...

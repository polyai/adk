from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TranscriptCorrections(_message.Message):
    __slots__ = ("corrections",)
    CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    corrections: _containers.RepeatedCompositeFieldContainer[TranscriptCorrection]
    def __init__(self, corrections: _Optional[_Iterable[_Union[TranscriptCorrection, _Mapping]]] = ...) -> None: ...

class TranscriptCorrection(_message.Message):
    __slots__ = ("id", "name", "description", "regular_expressions", "created_by", "created_at", "updated_by", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    regular_expressions: _containers.RepeatedCompositeFieldContainer[RegularExpression]
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[_Union[RegularExpression, _Mapping]]] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class RegularExpression(_message.Message):
    __slots__ = ("id", "regular_expression", "replacement", "replacement_type")
    ID_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    regular_expression: str
    replacement: str
    replacement_type: str
    def __init__(self, id: _Optional[str] = ..., regular_expression: _Optional[str] = ..., replacement: _Optional[str] = ..., replacement_type: _Optional[str] = ...) -> None: ...

class TranscriptCorrections_CreateTranscriptCorrections(_message.Message):
    __slots__ = ("id", "name", "description", "regular_expressions")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    regular_expressions: _containers.RepeatedCompositeFieldContainer[RegularExpression]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[_Union[RegularExpression, _Mapping]]] = ...) -> None: ...

class TranscriptCorrections_UpdateTranscriptCorrections(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: TranscriptCorrectionsUpdateData
    def __init__(self, data: _Optional[_Union[TranscriptCorrectionsUpdateData, _Mapping]] = ...) -> None: ...

class TranscriptCorrectionsUpdateData(_message.Message):
    __slots__ = ("corrections",)
    CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    corrections: _containers.RepeatedCompositeFieldContainer[TranscriptCorrection]
    def __init__(self, corrections: _Optional[_Iterable[_Union[TranscriptCorrection, _Mapping]]] = ...) -> None: ...

class TranscriptCorrections_DeleteTranscriptCorrections(_message.Message):
    __slots__ = ("transcript_corrections_id",)
    TRANSCRIPT_CORRECTIONS_ID_FIELD_NUMBER: _ClassVar[int]
    transcript_corrections_id: str
    def __init__(self, transcript_corrections_id: _Optional[str] = ...) -> None: ...

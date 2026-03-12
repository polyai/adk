from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class KeyphrasesBoosting(_message.Message):
    __slots__ = ("keyphrases_boosting",)
    KEYPHRASES_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    keyphrases_boosting: _containers.RepeatedCompositeFieldContainer[KeyphraseBoosting]
    def __init__(self, keyphrases_boosting: _Optional[_Iterable[_Union[KeyphraseBoosting, _Mapping]]] = ...) -> None: ...

class KeyphraseBoosting(_message.Message):
    __slots__ = ("id", "keyphrase", "level", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    KEYPHRASE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    keyphrase: str
    level: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., keyphrase: _Optional[str] = ..., level: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class KeyphraseBoosting_CreateKeyphrase(_message.Message):
    __slots__ = ("id", "keyphrase", "level")
    ID_FIELD_NUMBER: _ClassVar[int]
    KEYPHRASE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    id: str
    keyphrase: str
    level: str
    def __init__(self, id: _Optional[str] = ..., keyphrase: _Optional[str] = ..., level: _Optional[str] = ...) -> None: ...

class KeyphraseBoosting_UpdateKeyphrase(_message.Message):
    __slots__ = ("id", "keyphrase", "level")
    ID_FIELD_NUMBER: _ClassVar[int]
    KEYPHRASE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    id: str
    keyphrase: str
    level: str
    def __init__(self, id: _Optional[str] = ..., keyphrase: _Optional[str] = ..., level: _Optional[str] = ...) -> None: ...

class KeyphraseBoosting_DeleteKeyphrase(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

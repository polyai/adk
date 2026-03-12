from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TTSRule(_message.Message):
    __slots__ = ("id", "regex", "replacement", "case_sensitive", "created_at", "created_by", "updated_at", "updated_by", "language_code", "description", "position", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    REGEX_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CASE_SENSITIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    regex: str
    replacement: str
    case_sensitive: bool
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str
    language_code: str
    description: str
    position: int
    name: str
    def __init__(self, id: _Optional[str] = ..., regex: _Optional[str] = ..., replacement: _Optional[str] = ..., case_sensitive: bool = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[str] = ..., updated_by: _Optional[str] = ..., language_code: _Optional[str] = ..., description: _Optional[str] = ..., position: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class Pronunciations(_message.Message):
    __slots__ = ("pronunciations",)
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    pronunciations: _containers.RepeatedCompositeFieldContainer[TTSRule]
    def __init__(self, pronunciations: _Optional[_Iterable[_Union[TTSRule, _Mapping]]] = ...) -> None: ...

class Pronunciations_CreatePronunciation(_message.Message):
    __slots__ = ("id", "regex", "replacement", "case_sensitive", "language_code", "description", "position", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    REGEX_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CASE_SENSITIVE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    regex: str
    replacement: str
    case_sensitive: bool
    language_code: str
    description: str
    position: int
    name: str
    def __init__(self, id: _Optional[str] = ..., regex: _Optional[str] = ..., replacement: _Optional[str] = ..., case_sensitive: bool = ..., language_code: _Optional[str] = ..., description: _Optional[str] = ..., position: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class Pronunciations_UpdatePronunciation(_message.Message):
    __slots__ = ("id", "regex", "replacement", "case_sensitive", "language_code", "description", "position", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    REGEX_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CASE_SENSITIVE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    regex: str
    replacement: str
    case_sensitive: bool
    language_code: str
    description: str
    position: int
    name: str
    def __init__(self, id: _Optional[str] = ..., regex: _Optional[str] = ..., replacement: _Optional[str] = ..., case_sensitive: bool = ..., language_code: _Optional[str] = ..., description: _Optional[str] = ..., position: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class Pronunciations_DeletePronunciation(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Pronunciations_ReorderPronunciations(_message.Message):
    __slots__ = ("new_positions",)
    NEW_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    new_positions: _containers.RepeatedCompositeFieldContainer[PronunciationPositionUpdate]
    def __init__(self, new_positions: _Optional[_Iterable[_Union[PronunciationPositionUpdate, _Mapping]]] = ...) -> None: ...

class PronunciationPositionUpdate(_message.Message):
    __slots__ = ("id", "position")
    ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    id: str
    position: int
    def __init__(self, id: _Optional[str] = ..., position: _Optional[int] = ...) -> None: ...

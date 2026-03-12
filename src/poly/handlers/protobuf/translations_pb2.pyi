from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LocalizedText(_message.Message):
    __slots__ = ("language_code", "text", "is_auto_translated")
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    IS_AUTO_TRANSLATED_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    text: str
    is_auto_translated: bool
    def __init__(self, language_code: _Optional[str] = ..., text: _Optional[str] = ..., is_auto_translated: bool = ...) -> None: ...

class TranslationEntry(_message.Message):
    __slots__ = ("id", "translation_key", "translations", "created_at", "updated_at", "created_by", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_KEY_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    translation_key: str
    translations: _containers.RepeatedCompositeFieldContainer[LocalizedText]
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., translation_key: _Optional[str] = ..., translations: _Optional[_Iterable[_Union[LocalizedText, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Translations(_message.Message):
    __slots__ = ("translations",)
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    translations: _containers.RepeatedCompositeFieldContainer[TranslationEntry]
    def __init__(self, translations: _Optional[_Iterable[_Union[TranslationEntry, _Mapping]]] = ...) -> None: ...

class UpdateEntry(_message.Message):
    __slots__ = ("language_code", "text", "is_auto_translated")
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    IS_AUTO_TRANSLATED_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    text: str
    is_auto_translated: bool
    def __init__(self, language_code: _Optional[str] = ..., text: _Optional[str] = ..., is_auto_translated: bool = ...) -> None: ...

class LanguageHubTranslations_Create(_message.Message):
    __slots__ = ("id", "translation_key", "translations")
    ID_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_KEY_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    translation_key: str
    translations: _containers.RepeatedCompositeFieldContainer[LocalizedText]
    def __init__(self, id: _Optional[str] = ..., translation_key: _Optional[str] = ..., translations: _Optional[_Iterable[_Union[LocalizedText, _Mapping]]] = ...) -> None: ...

class LanguageHubTranslations_Update(_message.Message):
    __slots__ = ("id", "translation_key", "translations")
    ID_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_KEY_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    translation_key: str
    translations: _containers.RepeatedCompositeFieldContainer[UpdateEntry]
    def __init__(self, id: _Optional[str] = ..., translation_key: _Optional[str] = ..., translations: _Optional[_Iterable[_Union[UpdateEntry, _Mapping]]] = ...) -> None: ...

class LanguageHubTranslations_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

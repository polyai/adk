from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OutboundTemplateReferences(_message.Message):
    __slots__ = ("translations",)
    class TranslationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    translations: _containers.ScalarMap[str, bool]
    def __init__(self, translations: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class TemplateVariable(_message.Message):
    __slots__ = ("id", "name", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class OutboundTemplates(_message.Message):
    __slots__ = ("templates", "template_variables")
    TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VARIABLES_FIELD_NUMBER: _ClassVar[int]
    templates: _containers.RepeatedCompositeFieldContainer[OutboundTemplate]
    template_variables: _containers.RepeatedCompositeFieldContainer[TemplateVariable]
    def __init__(self, templates: _Optional[_Iterable[_Union[OutboundTemplate, _Mapping]]] = ..., template_variables: _Optional[_Iterable[_Union[TemplateVariable, _Mapping]]] = ...) -> None: ...

class OutboundTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "channel", "references", "created_at", "created_by", "updated_at", "updated_by", "active", "show_opt_out")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    SHOW_OPT_OUT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    channel: str
    references: OutboundTemplateReferences
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    active: bool
    show_opt_out: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., channel: _Optional[str] = ..., references: _Optional[_Union[OutboundTemplateReferences, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., active: bool = ..., show_opt_out: bool = ...) -> None: ...

class OutboundTemplate_CreateTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "channel", "references", "active", "show_opt_out")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    SHOW_OPT_OUT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    channel: str
    references: OutboundTemplateReferences
    active: bool
    show_opt_out: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., channel: _Optional[str] = ..., references: _Optional[_Union[OutboundTemplateReferences, _Mapping]] = ..., active: bool = ..., show_opt_out: bool = ...) -> None: ...

class OutboundTemplate_UpdateTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "references", "active", "show_opt_out")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    SHOW_OPT_OUT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    references: OutboundTemplateReferences
    active: bool
    show_opt_out: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., references: _Optional[_Union[OutboundTemplateReferences, _Mapping]] = ..., active: bool = ..., show_opt_out: bool = ...) -> None: ...

class OutboundTemplate_DeleteTemplate(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundTemplate_DuplicateTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "channel", "references", "active", "show_opt_out")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    SHOW_OPT_OUT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    channel: str
    references: OutboundTemplateReferences
    active: bool
    show_opt_out: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., channel: _Optional[str] = ..., references: _Optional[_Union[OutboundTemplateReferences, _Mapping]] = ..., active: bool = ..., show_opt_out: bool = ...) -> None: ...

class OutboundTemplate_CreateTemplateVariable(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class OutboundTemplate_DeleteTemplateVariable(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

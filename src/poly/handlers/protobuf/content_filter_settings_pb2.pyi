from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ContentFilterSettings(_message.Message):
    __slots__ = ("type", "azure_config", "updated_by", "updated_at", "disabled")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    AZURE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    DISABLED_FIELD_NUMBER: _ClassVar[int]
    type: str
    azure_config: AzureContentFilter
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    disabled: bool
    def __init__(self, type: _Optional[str] = ..., azure_config: _Optional[_Union[AzureContentFilter, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., disabled: bool = ...) -> None: ...

class AzureContentFilterCategory(_message.Message):
    __slots__ = ("is_active", "precision")
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    PRECISION_FIELD_NUMBER: _ClassVar[int]
    is_active: bool
    precision: str
    def __init__(self, is_active: bool = ..., precision: _Optional[str] = ...) -> None: ...

class AzureContentFilter(_message.Message):
    __slots__ = ("violence", "hate", "sexual", "self_harm")
    VIOLENCE_FIELD_NUMBER: _ClassVar[int]
    HATE_FIELD_NUMBER: _ClassVar[int]
    SEXUAL_FIELD_NUMBER: _ClassVar[int]
    SELF_HARM_FIELD_NUMBER: _ClassVar[int]
    violence: AzureContentFilterCategory
    hate: AzureContentFilterCategory
    sexual: AzureContentFilterCategory
    self_harm: AzureContentFilterCategory
    def __init__(self, violence: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., hate: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., sexual: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., self_harm: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ...) -> None: ...

class ContentFilterSettings_UpdateContentFilterSettings(_message.Message):
    __slots__ = ("type", "azure_config", "disabled")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    AZURE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    DISABLED_FIELD_NUMBER: _ClassVar[int]
    type: str
    azure_config: AzureContentFilter
    disabled: bool
    def __init__(self, type: _Optional[str] = ..., azure_config: _Optional[_Union[AzureContentFilter, _Mapping]] = ..., disabled: bool = ...) -> None: ...

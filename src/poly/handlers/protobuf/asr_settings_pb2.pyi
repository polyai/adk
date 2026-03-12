from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ASRSettings(_message.Message):
    __slots__ = ("barge_in", "latency_config", "updated_by", "updated_at")
    BARGE_IN_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    barge_in: bool
    latency_config: LatencyConfig
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, barge_in: bool = ..., latency_config: _Optional[_Union[LatencyConfig, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class LatencyConfig(_message.Message):
    __slots__ = ("interaction_style",)
    INTERACTION_STYLE_FIELD_NUMBER: _ClassVar[int]
    interaction_style: str
    def __init__(self, interaction_style: _Optional[str] = ...) -> None: ...

class ASRSettings_UpdateASRSettings(_message.Message):
    __slots__ = ("barge_in", "latency_config")
    BARGE_IN_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    barge_in: bool
    latency_config: LatencyConfig
    def __init__(self, barge_in: bool = ..., latency_config: _Optional[_Union[LatencyConfig, _Mapping]] = ...) -> None: ...

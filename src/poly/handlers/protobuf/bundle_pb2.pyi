from poly.handlers.protobuf import snapshot_pb2 as _snapshot_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RagDatabase(_message.Message):
    __slots__ = ("embedding_model", "embeddings_map")
    class EmbeddingsMapEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    EMBEDDING_MODEL_FIELD_NUMBER: _ClassVar[int]
    EMBEDDINGS_MAP_FIELD_NUMBER: _ClassVar[int]
    embedding_model: str
    embeddings_map: _containers.ScalarMap[str, bytes]
    def __init__(self, embedding_model: _Optional[str] = ..., embeddings_map: _Optional[_Mapping[str, bytes]] = ...) -> None: ...

class RealTimeConfiguration(_message.Message):
    __slots__ = ("schema", "config")
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    schema: _struct_pb2.Struct
    config: _struct_pb2.Struct
    def __init__(self, schema: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Bundle(_message.Message):
    __slots__ = ("snapshot", "rt_configurations", "rag_database")
    class RtConfigurationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: RealTimeConfiguration
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[RealTimeConfiguration, _Mapping]] = ...) -> None: ...
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    RT_CONFIGURATIONS_FIELD_NUMBER: _ClassVar[int]
    RAG_DATABASE_FIELD_NUMBER: _ClassVar[int]
    snapshot: _snapshot_pb2.Snapshot
    rt_configurations: _containers.MessageMap[str, RealTimeConfiguration]
    rag_database: RagDatabase
    def __init__(self, snapshot: _Optional[_Union[_snapshot_pb2.Snapshot, _Mapping]] = ..., rt_configurations: _Optional[_Mapping[str, RealTimeConfiguration]] = ..., rag_database: _Optional[_Union[RagDatabase, _Mapping]] = ...) -> None: ...

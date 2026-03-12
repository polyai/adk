from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExampleQueries(_message.Message):
    __slots__ = ("queries",)
    QUERIES_FIELD_NUMBER: _ClassVar[int]
    queries: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, queries: _Optional[_Iterable[str]] = ...) -> None: ...

class TopicReferences(_message.Message):
    __slots__ = ("sms", "handoff", "attributes", "global_functions", "variables")
    class SmsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class HandoffEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class GlobalFunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    SMS_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    sms: _containers.ScalarMap[str, bool]
    handoff: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    global_functions: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, sms: _Optional[_Mapping[str, bool]] = ..., handoff: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., global_functions: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class KnowledgeBase(_message.Message):
    __slots__ = ("topics", "embedding_model")
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_MODEL_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.RepeatedCompositeFieldContainer[KnowledgeBaseTopic]
    embedding_model: str
    def __init__(self, topics: _Optional[_Iterable[_Union[KnowledgeBaseTopic, _Mapping]]] = ..., embedding_model: _Optional[str] = ...) -> None: ...

class KnowledgeBaseTopic(_message.Message):
    __slots__ = ("id", "name", "content", "actions", "example_queries", "references", "created_at", "created_by", "updated_at", "updated_by", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_QUERIES_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    content: str
    actions: str
    example_queries: ExampleQueries
    references: TopicReferences
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., content: _Optional[str] = ..., actions: _Optional[str] = ..., example_queries: _Optional[_Union[ExampleQueries, _Mapping]] = ..., references: _Optional[_Union[TopicReferences, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., is_active: bool = ...) -> None: ...

class KnowledgeBase_CreateTopic(_message.Message):
    __slots__ = ("id", "name", "content", "actions", "example_queries", "references", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_QUERIES_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    content: str
    actions: str
    example_queries: ExampleQueries
    references: TopicReferences
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., content: _Optional[str] = ..., actions: _Optional[str] = ..., example_queries: _Optional[_Union[ExampleQueries, _Mapping]] = ..., references: _Optional[_Union[TopicReferences, _Mapping]] = ..., is_active: bool = ...) -> None: ...

class KnowledgeBase_UpdateTopic(_message.Message):
    __slots__ = ("id", "name", "content", "actions", "example_queries", "references", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_QUERIES_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    content: str
    actions: str
    example_queries: ExampleQueries
    references: TopicReferences
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., content: _Optional[str] = ..., actions: _Optional[str] = ..., example_queries: _Optional[_Union[ExampleQueries, _Mapping]] = ..., references: _Optional[_Union[TopicReferences, _Mapping]] = ..., is_active: bool = ...) -> None: ...

class KnowledgeBase_DeleteTopic(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class KnowledgeBase_ToggleTopicStatus(_message.Message):
    __slots__ = ("id", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., is_active: bool = ...) -> None: ...

class KnowledgeBase_ImportTopics(_message.Message):
    __slots__ = ("created", "updated", "deleted", "source", "metadata")
    CREATED_FIELD_NUMBER: _ClassVar[int]
    UPDATED_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    created: _containers.RepeatedCompositeFieldContainer[KnowledgeBase_CreateTopic]
    updated: _containers.RepeatedCompositeFieldContainer[KnowledgeBase_UpdateTopic]
    deleted: _containers.RepeatedScalarFieldContainer[str]
    source: str
    metadata: ImportMetadata
    def __init__(self, created: _Optional[_Iterable[_Union[KnowledgeBase_CreateTopic, _Mapping]]] = ..., updated: _Optional[_Iterable[_Union[KnowledgeBase_UpdateTopic, _Mapping]]] = ..., deleted: _Optional[_Iterable[str]] = ..., source: _Optional[str] = ..., metadata: _Optional[_Union[ImportMetadata, _Mapping]] = ...) -> None: ...

class ImportMetadata(_message.Message):
    __slots__ = ("total_topics", "import_timestamp", "file_name")
    TOTAL_TOPICS_FIELD_NUMBER: _ClassVar[int]
    IMPORT_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    total_topics: int
    import_timestamp: str
    file_name: str
    def __init__(self, total_topics: _Optional[int] = ..., import_timestamp: _Optional[str] = ..., file_name: _Optional[str] = ...) -> None: ...

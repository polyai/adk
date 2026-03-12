from google.protobuf import timestamp_pb2 as _timestamp_pb2
from poly_platform.ragdoll.pb import ragdoll_types_pb2 as _ragdoll_types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[ErrorCode]
    KNOWLEDGE_BASE_NOT_EXISTS: _ClassVar[ErrorCode]
    INVALID_ARGUMENT: _ClassVar[ErrorCode]
    REDIS_TIMEOUT: _ClassVar[ErrorCode]
    COMPUTE_TIMEOUT: _ClassVar[ErrorCode]
    KNOWLEDGE_BASE_ALREADY_EXISTS: _ClassVar[ErrorCode]
NONE: ErrorCode
KNOWLEDGE_BASE_NOT_EXISTS: ErrorCode
INVALID_ARGUMENT: ErrorCode
REDIS_TIMEOUT: ErrorCode
COMPUTE_TIMEOUT: ErrorCode
KNOWLEDGE_BASE_ALREADY_EXISTS: ErrorCode

class Error(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: ErrorCode
    message: str
    def __init__(self, code: _Optional[_Union[ErrorCode, str]] = ..., message: _Optional[str] = ...) -> None: ...

class ListTopicsParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class ListTopicsOutput(_message.Message):
    __slots__ = ("topics", "uninstantiated_topics", "updated_at")
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    UNINSTANTIATED_TOPICS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    uninstantiated_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., uninstantiated_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListTopicsResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: ListTopicsOutput
    error: Error
    def __init__(self, output: _Optional[_Union[ListTopicsOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class QueryTopicsParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version", "query_text", "top_k", "threshold", "variant_id", "client_env")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    QUERY_TEXT_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    query_text: str
    top_k: int
    threshold: float
    variant_id: str
    client_env: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ..., query_text: _Optional[str] = ..., top_k: _Optional[int] = ..., threshold: _Optional[float] = ..., variant_id: _Optional[str] = ..., client_env: _Optional[str] = ...) -> None: ...

class QueryTopicResult(_message.Message):
    __slots__ = ("topic", "distance")
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    topic: _ragdoll_types_pb2.Topic
    distance: float
    def __init__(self, topic: _Optional[_Union[_ragdoll_types_pb2.Topic, _Mapping]] = ..., distance: _Optional[float] = ...) -> None: ...

class QueryTopicsOutput(_message.Message):
    __slots__ = ("results", "required_loading")
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_LOADING_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[QueryTopicResult]
    required_loading: bool
    def __init__(self, results: _Optional[_Iterable[_Union[QueryTopicResult, _Mapping]]] = ..., required_loading: bool = ...) -> None: ...

class QueryTopicsResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: QueryTopicsOutput
    error: Error
    def __init__(self, output: _Optional[_Union[QueryTopicsOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class EnsureReadyParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version", "client_env")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    client_env: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ..., client_env: _Optional[str] = ...) -> None: ...

class EnsureReadyOutput(_message.Message):
    __slots__ = ("required_loading",)
    REQUIRED_LOADING_FIELD_NUMBER: _ClassVar[int]
    required_loading: bool
    def __init__(self, required_loading: bool = ...) -> None: ...

class EnsureReadyResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: EnsureReadyOutput
    error: Error
    def __init__(self, output: _Optional[_Union[EnsureReadyOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class UpdateTopicsParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version", "version_to_create", "dry_run", "create_topics", "update_topics", "delete_topic_ids", "new_updated_at", "uninstantiated_topics")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    VERSION_TO_CREATE_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    CREATE_TOPICS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TOPICS_FIELD_NUMBER: _ClassVar[int]
    DELETE_TOPIC_IDS_FIELD_NUMBER: _ClassVar[int]
    NEW_UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UNINSTANTIATED_TOPICS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    version_to_create: str
    dry_run: bool
    create_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    update_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    delete_topic_ids: _containers.RepeatedScalarFieldContainer[str]
    new_updated_at: _timestamp_pb2.Timestamp
    uninstantiated_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ..., version_to_create: _Optional[str] = ..., dry_run: bool = ..., create_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., update_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., delete_topic_ids: _Optional[_Iterable[str]] = ..., new_updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., uninstantiated_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ...) -> None: ...

class UpdateTopicsOutput(_message.Message):
    __slots__ = ("num_created", "num_deleted", "num_updated", "new_updated_at")
    NUM_CREATED_FIELD_NUMBER: _ClassVar[int]
    NUM_DELETED_FIELD_NUMBER: _ClassVar[int]
    NUM_UPDATED_FIELD_NUMBER: _ClassVar[int]
    NEW_UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    num_created: int
    num_deleted: int
    num_updated: int
    new_updated_at: _timestamp_pb2.Timestamp
    def __init__(self, num_created: _Optional[int] = ..., num_deleted: _Optional[int] = ..., num_updated: _Optional[int] = ..., new_updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class UpdateTopicsResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: UpdateTopicsOutput
    error: Error
    def __init__(self, output: _Optional[_Union[UpdateTopicsOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class CreateEphemeralParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version", "version_to_create", "updated_at", "expiry")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    VERSION_TO_CREATE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    EXPIRY_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    version_to_create: str
    updated_at: _timestamp_pb2.Timestamp
    expiry: int
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ..., version_to_create: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., expiry: _Optional[int] = ...) -> None: ...

class CreateEphemeralOutput(_message.Message):
    __slots__ = ("index_size", "updated_at")
    INDEX_SIZE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    index_size: int
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, index_size: _Optional[int] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CreateEphemeralResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: CreateEphemeralOutput
    error: Error
    def __init__(self, output: _Optional[_Union[CreateEphemeralOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class UpdateInplaceParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version", "expected_updated_at", "new_updated_at", "create_topics", "update_topics", "delete_topic_ids", "uninstantiated_topics")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    NEW_UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATE_TOPICS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TOPICS_FIELD_NUMBER: _ClassVar[int]
    DELETE_TOPIC_IDS_FIELD_NUMBER: _ClassVar[int]
    UNINSTANTIATED_TOPICS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    expected_updated_at: _timestamp_pb2.Timestamp
    new_updated_at: _timestamp_pb2.Timestamp
    create_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    update_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    delete_topic_ids: _containers.RepeatedScalarFieldContainer[str]
    uninstantiated_topics: _containers.RepeatedCompositeFieldContainer[_ragdoll_types_pb2.Topic]
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ..., expected_updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., new_updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., create_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., update_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ..., delete_topic_ids: _Optional[_Iterable[str]] = ..., uninstantiated_topics: _Optional[_Iterable[_Union[_ragdoll_types_pb2.Topic, _Mapping]]] = ...) -> None: ...

class UpdateInplaceOutput(_message.Message):
    __slots__ = ("num_created", "num_deleted", "num_updated", "new_updated_at", "create_topics_warning_ids", "update_topics_warning_ids", "delete_topics_warning_ids")
    NUM_CREATED_FIELD_NUMBER: _ClassVar[int]
    NUM_DELETED_FIELD_NUMBER: _ClassVar[int]
    NUM_UPDATED_FIELD_NUMBER: _ClassVar[int]
    NEW_UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATE_TOPICS_WARNING_IDS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TOPICS_WARNING_IDS_FIELD_NUMBER: _ClassVar[int]
    DELETE_TOPICS_WARNING_IDS_FIELD_NUMBER: _ClassVar[int]
    num_created: int
    num_deleted: int
    num_updated: int
    new_updated_at: _timestamp_pb2.Timestamp
    create_topics_warning_ids: _containers.RepeatedScalarFieldContainer[str]
    update_topics_warning_ids: _containers.RepeatedScalarFieldContainer[str]
    delete_topics_warning_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, num_created: _Optional[int] = ..., num_deleted: _Optional[int] = ..., num_updated: _Optional[int] = ..., new_updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., create_topics_warning_ids: _Optional[_Iterable[str]] = ..., update_topics_warning_ids: _Optional[_Iterable[str]] = ..., delete_topics_warning_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class UpdateInplaceResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: UpdateInplaceOutput
    error: Error
    def __init__(self, output: _Optional[_Union[UpdateInplaceOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class GetMetadataParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class GetMetadataOutput(_message.Message):
    __slots__ = ("index_size", "updated_at")
    INDEX_SIZE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    index_size: int
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, index_size: _Optional[int] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetMetadataReponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: GetMetadataOutput
    error: Error
    def __init__(self, output: _Optional[_Union[GetMetadataOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class DeleteCachedParams(_message.Message):
    __slots__ = ("account_id", "project_id", "version")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    version: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class DeleteCachedOutput(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DeleteCachedResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: DeleteCachedOutput
    error: Error
    def __init__(self, output: _Optional[_Union[DeleteCachedOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class UpdateModelParams(_message.Message):
    __slots__ = ("account_id", "project_id", "embedding_model", "version")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_MODEL_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    embedding_model: str
    version: str
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., embedding_model: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class UpdateModelOutput(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UpdateModelResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: UpdateModelOutput
    error: Error
    def __init__(self, output: _Optional[_Union[UpdateModelOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class TextToEmbed(_message.Message):
    __slots__ = ("id", "name", "content")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    content: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class EmbedTextsParams(_message.Message):
    __slots__ = ("account_id", "project_id", "embedding_model", "texts")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_MODEL_FIELD_NUMBER: _ClassVar[int]
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    project_id: str
    embedding_model: str
    texts: _containers.RepeatedCompositeFieldContainer[TextToEmbed]
    def __init__(self, account_id: _Optional[str] = ..., project_id: _Optional[str] = ..., embedding_model: _Optional[str] = ..., texts: _Optional[_Iterable[_Union[TextToEmbed, _Mapping]]] = ...) -> None: ...

class EmbeddedText(_message.Message):
    __slots__ = ("embedding",)
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    embedding: bytes
    def __init__(self, embedding: _Optional[bytes] = ...) -> None: ...

class EmbedTextsOutput(_message.Message):
    __slots__ = ("embedded_texts",)
    EMBEDDED_TEXTS_FIELD_NUMBER: _ClassVar[int]
    embedded_texts: _containers.RepeatedCompositeFieldContainer[EmbeddedText]
    def __init__(self, embedded_texts: _Optional[_Iterable[_Union[EmbeddedText, _Mapping]]] = ...) -> None: ...

class EmbedTextsResponse(_message.Message):
    __slots__ = ("output", "error")
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    output: EmbedTextsOutput
    error: Error
    def __init__(self, output: _Optional[_Union[EmbedTextsOutput, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

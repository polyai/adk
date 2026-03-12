from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Attribute(_message.Message):
    __slots__ = ("id", "name", "attribute_type", "archived", "references", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    attribute_type: str
    archived: bool
    references: AttributeReferences
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., attribute_type: _Optional[str] = ..., archived: bool = ..., references: _Optional[_Union[AttributeReferences, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Variant(_message.Message):
    __slots__ = ("id", "name", "is_default", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    is_default: bool
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., is_default: bool = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Variants(_message.Message):
    __slots__ = ("variants",)
    VARIANTS_FIELD_NUMBER: _ClassVar[int]
    variants: _containers.RepeatedCompositeFieldContainer[Variant]
    def __init__(self, variants: _Optional[_Iterable[_Union[Variant, _Mapping]]] = ...) -> None: ...

class VariantManagement(_message.Message):
    __slots__ = ("variants", "attributes", "variant_attribute_values")
    VARIANTS_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ATTRIBUTE_VALUES_FIELD_NUMBER: _ClassVar[int]
    variants: _containers.RepeatedCompositeFieldContainer[Variant]
    attributes: _containers.RepeatedCompositeFieldContainer[Attribute]
    variant_attribute_values: VariantAttributeValues
    def __init__(self, variants: _Optional[_Iterable[_Union[Variant, _Mapping]]] = ..., attributes: _Optional[_Iterable[_Union[Attribute, _Mapping]]] = ..., variant_attribute_values: _Optional[_Union[VariantAttributeValues, _Mapping]] = ...) -> None: ...

class VariantAttributeValues(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: AttributeValues
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[AttributeValues, _Mapping]] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.MessageMap[str, AttributeValues]
    def __init__(self, values: _Optional[_Mapping[str, AttributeValues]] = ...) -> None: ...

class AttributeValues(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.ScalarMap[str, str]
    def __init__(self, values: _Optional[_Mapping[str, str]] = ...) -> None: ...

class VariantValues(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.ScalarMap[str, str]
    def __init__(self, values: _Optional[_Mapping[str, str]] = ...) -> None: ...

class AttributeReferences(_message.Message):
    __slots__ = ("topics", "flow_steps", "no_code_steps")
    class TopicsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class FlowStepsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class NoCodeStepsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.ScalarMap[str, bool]
    flow_steps: _containers.ScalarMap[str, bool]
    no_code_steps: _containers.ScalarMap[str, bool]
    def __init__(self, topics: _Optional[_Mapping[str, bool]] = ..., flow_steps: _Optional[_Mapping[str, bool]] = ..., no_code_steps: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Variant_CreateVariant(_message.Message):
    __slots__ = ("id", "name", "attribute_values")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_VALUES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    attribute_values: AttributeValues
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., attribute_values: _Optional[_Union[AttributeValues, _Mapping]] = ...) -> None: ...

class Variant_UpdateVariant(_message.Message):
    __slots__ = ("id", "name", "attribute_values")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_VALUES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    attribute_values: AttributeValues
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., attribute_values: _Optional[_Union[AttributeValues, _Mapping]] = ...) -> None: ...

class Variant_DeleteVariant(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Variant_CreateAttribute(_message.Message):
    __slots__ = ("id", "name", "references", "variant_values")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    VARIANT_VALUES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    references: AttributeReferences
    variant_values: VariantValues
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., references: _Optional[_Union[AttributeReferences, _Mapping]] = ..., variant_values: _Optional[_Union[VariantValues, _Mapping]] = ...) -> None: ...

class Variant_UpdateAttribute(_message.Message):
    __slots__ = ("id", "name", "references", "variant_values")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    VARIANT_VALUES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    references: AttributeReferences
    variant_values: VariantValues
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., references: _Optional[_Union[AttributeReferences, _Mapping]] = ..., variant_values: _Optional[_Union[VariantValues, _Mapping]] = ...) -> None: ...

class Variant_DeleteAttribute(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Variant_SetDefaultVariant(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Variant_ImportVariantForCsv(_message.Message):
    __slots__ = ("id", "name", "is_default")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    is_default: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., is_default: bool = ...) -> None: ...

class Variant_ImportAttributeForCsv(_message.Message):
    __slots__ = ("id", "name", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    references: AttributeReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., references: _Optional[_Union[AttributeReferences, _Mapping]] = ...) -> None: ...

class Variant_ImportVariantAttributeValuesForCsv(_message.Message):
    __slots__ = ("variant_id", "attribute_id", "value")
    VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_ID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    variant_id: str
    attribute_id: str
    value: str
    def __init__(self, variant_id: _Optional[str] = ..., attribute_id: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class Variant_ImportVariants(_message.Message):
    __slots__ = ("variants", "attributes", "variant_attribute_values", "deleted_variant_ids", "deleted_attribute_ids")
    VARIANTS_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ATTRIBUTE_VALUES_FIELD_NUMBER: _ClassVar[int]
    DELETED_VARIANT_IDS_FIELD_NUMBER: _ClassVar[int]
    DELETED_ATTRIBUTE_IDS_FIELD_NUMBER: _ClassVar[int]
    variants: _containers.RepeatedCompositeFieldContainer[Variant_ImportVariantForCsv]
    attributes: _containers.RepeatedCompositeFieldContainer[Variant_ImportAttributeForCsv]
    variant_attribute_values: _containers.RepeatedCompositeFieldContainer[Variant_ImportVariantAttributeValuesForCsv]
    deleted_variant_ids: _containers.RepeatedScalarFieldContainer[str]
    deleted_attribute_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, variants: _Optional[_Iterable[_Union[Variant_ImportVariantForCsv, _Mapping]]] = ..., attributes: _Optional[_Iterable[_Union[Variant_ImportAttributeForCsv, _Mapping]]] = ..., variant_attribute_values: _Optional[_Iterable[_Union[Variant_ImportVariantAttributeValuesForCsv, _Mapping]]] = ..., deleted_variant_ids: _Optional[_Iterable[str]] = ..., deleted_attribute_ids: _Optional[_Iterable[str]] = ...) -> None: ...

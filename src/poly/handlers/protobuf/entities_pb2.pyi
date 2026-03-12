from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EntityReferences(_message.Message):
    __slots__ = ("flow_steps", "no_code_steps")
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
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    flow_steps: _containers.ScalarMap[str, bool]
    no_code_steps: _containers.ScalarMap[str, bool]
    def __init__(self, flow_steps: _Optional[_Mapping[str, bool]] = ..., no_code_steps: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Entities(_message.Message):
    __slots__ = ("entities",)
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    entities: _containers.RepeatedCompositeFieldContainer[Entity]
    def __init__(self, entities: _Optional[_Iterable[_Union[Entity, _Mapping]]] = ...) -> None: ...

class Entity(_message.Message):
    __slots__ = ("id", "name", "type", "description", "created_by", "created_at", "updated_by", "updated_at", "references", "numeric", "alphanumeric", "enum", "date", "phone_number", "time", "address", "free_text", "name_config")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    ENUM_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    FREE_TEXT_FIELD_NUMBER: _ClassVar[int]
    NAME_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    type: str
    description: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    references: EntityReferences
    numeric: NumberConfig
    alphanumeric: AlphanumericConfig
    enum: MultipleOptionsConfig
    date: DateConfig
    phone_number: PhoneNumberConfig
    time: TimeConfig
    address: AddressConfig
    free_text: FreeTextConfig
    name_config: NameConfig
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[str] = ..., description: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., references: _Optional[_Union[EntityReferences, _Mapping]] = ..., numeric: _Optional[_Union[NumberConfig, _Mapping]] = ..., alphanumeric: _Optional[_Union[AlphanumericConfig, _Mapping]] = ..., enum: _Optional[_Union[MultipleOptionsConfig, _Mapping]] = ..., date: _Optional[_Union[DateConfig, _Mapping]] = ..., phone_number: _Optional[_Union[PhoneNumberConfig, _Mapping]] = ..., time: _Optional[_Union[TimeConfig, _Mapping]] = ..., address: _Optional[_Union[AddressConfig, _Mapping]] = ..., free_text: _Optional[_Union[FreeTextConfig, _Mapping]] = ..., name_config: _Optional[_Union[NameConfig, _Mapping]] = ...) -> None: ...

class Entity_Create(_message.Message):
    __slots__ = ("id", "name", "type", "description", "references", "numeric", "alphanumeric", "enum", "date", "phone_number", "time", "address", "free_text", "name_config")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    ENUM_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    FREE_TEXT_FIELD_NUMBER: _ClassVar[int]
    NAME_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    type: str
    description: str
    references: EntityReferences
    numeric: NumberConfig
    alphanumeric: AlphanumericConfig
    enum: MultipleOptionsConfig
    date: DateConfig
    phone_number: PhoneNumberConfig
    time: TimeConfig
    address: AddressConfig
    free_text: FreeTextConfig
    name_config: NameConfig
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[str] = ..., description: _Optional[str] = ..., references: _Optional[_Union[EntityReferences, _Mapping]] = ..., numeric: _Optional[_Union[NumberConfig, _Mapping]] = ..., alphanumeric: _Optional[_Union[AlphanumericConfig, _Mapping]] = ..., enum: _Optional[_Union[MultipleOptionsConfig, _Mapping]] = ..., date: _Optional[_Union[DateConfig, _Mapping]] = ..., phone_number: _Optional[_Union[PhoneNumberConfig, _Mapping]] = ..., time: _Optional[_Union[TimeConfig, _Mapping]] = ..., address: _Optional[_Union[AddressConfig, _Mapping]] = ..., free_text: _Optional[_Union[FreeTextConfig, _Mapping]] = ..., name_config: _Optional[_Union[NameConfig, _Mapping]] = ...) -> None: ...

class Entity_Update(_message.Message):
    __slots__ = ("id", "name", "type", "description", "references", "numeric", "alphanumeric", "enum", "date", "phone_number", "time", "address", "free_text", "name_config")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    ENUM_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    FREE_TEXT_FIELD_NUMBER: _ClassVar[int]
    NAME_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    type: str
    description: str
    references: EntityReferences
    numeric: NumberConfig
    alphanumeric: AlphanumericConfig
    enum: MultipleOptionsConfig
    date: DateConfig
    phone_number: PhoneNumberConfig
    time: TimeConfig
    address: AddressConfig
    free_text: FreeTextConfig
    name_config: NameConfig
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[str] = ..., description: _Optional[str] = ..., references: _Optional[_Union[EntityReferences, _Mapping]] = ..., numeric: _Optional[_Union[NumberConfig, _Mapping]] = ..., alphanumeric: _Optional[_Union[AlphanumericConfig, _Mapping]] = ..., enum: _Optional[_Union[MultipleOptionsConfig, _Mapping]] = ..., date: _Optional[_Union[DateConfig, _Mapping]] = ..., phone_number: _Optional[_Union[PhoneNumberConfig, _Mapping]] = ..., time: _Optional[_Union[TimeConfig, _Mapping]] = ..., address: _Optional[_Union[AddressConfig, _Mapping]] = ..., free_text: _Optional[_Union[FreeTextConfig, _Mapping]] = ..., name_config: _Optional[_Union[NameConfig, _Mapping]] = ...) -> None: ...

class Entity_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class NumberConfig(_message.Message):
    __slots__ = ("has_decimal", "has_range", "min", "max")
    HAS_DECIMAL_FIELD_NUMBER: _ClassVar[int]
    HAS_RANGE_FIELD_NUMBER: _ClassVar[int]
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    has_decimal: bool
    has_range: bool
    min: float
    max: float
    def __init__(self, has_decimal: bool = ..., has_range: bool = ..., min: _Optional[float] = ..., max: _Optional[float] = ...) -> None: ...

class AlphanumericConfig(_message.Message):
    __slots__ = ("enabled", "validation_type", "regular_expression")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    validation_type: str
    regular_expression: str
    def __init__(self, enabled: bool = ..., validation_type: _Optional[str] = ..., regular_expression: _Optional[str] = ...) -> None: ...

class MultipleOptionsConfig(_message.Message):
    __slots__ = ("options",)
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    options: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, options: _Optional[_Iterable[str]] = ...) -> None: ...

class DateConfig(_message.Message):
    __slots__ = ("relative_date",)
    RELATIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    relative_date: bool
    def __init__(self, relative_date: bool = ...) -> None: ...

class PhoneNumberConfig(_message.Message):
    __slots__ = ("enabled", "country_codes")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_CODES_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    country_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, enabled: bool = ..., country_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class TimeConfig(_message.Message):
    __slots__ = ("enabled", "start_time", "end_time")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    start_time: str
    end_time: str
    def __init__(self, enabled: bool = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class AddressConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class FreeTextConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NameConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

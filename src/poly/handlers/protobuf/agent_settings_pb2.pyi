from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AgentSettings(_message.Message):
    __slots__ = ("greeting", "personality", "role", "disclaimer_message", "rules", "language_behaviors")
    class LanguageBehaviorsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: LanguageBehavior
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[LanguageBehavior, _Mapping]] = ...) -> None: ...
    GREETING_FIELD_NUMBER: _ClassVar[int]
    PERSONALITY_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RULES_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_BEHAVIORS_FIELD_NUMBER: _ClassVar[int]
    greeting: _containers.RepeatedCompositeFieldContainer[Greeting]
    personality: Personality
    role: Role
    disclaimer_message: _containers.RepeatedCompositeFieldContainer[DisclaimerMessage]
    rules: Rules
    language_behaviors: _containers.MessageMap[str, LanguageBehavior]
    def __init__(self, greeting: _Optional[_Iterable[_Union[Greeting, _Mapping]]] = ..., personality: _Optional[_Union[Personality, _Mapping]] = ..., role: _Optional[_Union[Role, _Mapping]] = ..., disclaimer_message: _Optional[_Iterable[_Union[DisclaimerMessage, _Mapping]]] = ..., rules: _Optional[_Union[Rules, _Mapping]] = ..., language_behaviors: _Optional[_Mapping[str, LanguageBehavior]] = ...) -> None: ...

class Greeting(_message.Message):
    __slots__ = ("welcome_message", "created_at", "created_by", "updated_at", "updated_by", "references", "language_code")
    WELCOME_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    welcome_message: str
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    references: GreetingReferences
    language_code: str
    def __init__(self, welcome_message: _Optional[str] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., references: _Optional[_Union[GreetingReferences, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class Greeting_UpdateGreeting(_message.Message):
    __slots__ = ("welcome_message", "references", "language_code")
    WELCOME_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    welcome_message: str
    references: GreetingReferences
    language_code: str
    def __init__(self, welcome_message: _Optional[str] = ..., references: _Optional[_Union[GreetingReferences, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class GreetingReferences(_message.Message):
    __slots__ = ("variables",)
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Adjectives(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.ScalarMap[str, bool]
    def __init__(self, values: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Personality(_message.Message):
    __slots__ = ("adjectives", "custom", "created_at", "created_by", "updated_at", "updated_by", "references")
    class AdjectivesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    ADJECTIVES_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    adjectives: _containers.ScalarMap[str, bool]
    custom: str
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    references: PersonalityReferences
    def __init__(self, adjectives: _Optional[_Mapping[str, bool]] = ..., custom: _Optional[str] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., references: _Optional[_Union[PersonalityReferences, _Mapping]] = ...) -> None: ...

class Personality_UpdatePersonality(_message.Message):
    __slots__ = ("adjectives", "custom", "references")
    ADJECTIVES_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    adjectives: Adjectives
    custom: str
    references: PersonalityReferences
    def __init__(self, adjectives: _Optional[_Union[Adjectives, _Mapping]] = ..., custom: _Optional[str] = ..., references: _Optional[_Union[PersonalityReferences, _Mapping]] = ...) -> None: ...

class PersonalityReferences(_message.Message):
    __slots__ = ("variables",)
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Role(_message.Message):
    __slots__ = ("value", "additional_info", "custom", "created_at", "created_by", "updated_at", "updated_by", "references")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_INFO_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    value: str
    additional_info: str
    custom: str
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    references: RoleReferences
    def __init__(self, value: _Optional[str] = ..., additional_info: _Optional[str] = ..., custom: _Optional[str] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., references: _Optional[_Union[RoleReferences, _Mapping]] = ...) -> None: ...

class Role_UpdateRole(_message.Message):
    __slots__ = ("value", "additional_info", "custom", "references")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_INFO_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    value: str
    additional_info: str
    custom: str
    references: RoleReferences
    def __init__(self, value: _Optional[str] = ..., additional_info: _Optional[str] = ..., custom: _Optional[str] = ..., references: _Optional[_Union[RoleReferences, _Mapping]] = ...) -> None: ...

class RoleReferences(_message.Message):
    __slots__ = ("variables",)
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class DisclaimerMessage(_message.Message):
    __slots__ = ("is_enabled", "message", "ringing_tone", "created_at", "created_by", "updated_at", "updated_by", "language_code")
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RINGING_TONE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    is_enabled: bool
    message: str
    ringing_tone: AudioToPlay
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    language_code: str
    def __init__(self, is_enabled: bool = ..., message: _Optional[str] = ..., ringing_tone: _Optional[_Union[AudioToPlay, _Mapping]] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., language_code: _Optional[str] = ...) -> None: ...

class DisclaimerMessage_UpdateDisclaimerMessage(_message.Message):
    __slots__ = ("is_enabled", "message", "ringing_tone", "language_code")
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RINGING_TONE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    is_enabled: bool
    message: str
    ringing_tone: UpdateRingingTone
    language_code: str
    def __init__(self, is_enabled: bool = ..., message: _Optional[str] = ..., ringing_tone: _Optional[_Union[UpdateRingingTone, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class UpdateRingingTone(_message.Message):
    __slots__ = ("s3_path", "original_filename", "public_url")
    S3_PATH_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_FILENAME_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_URL_FIELD_NUMBER: _ClassVar[int]
    s3_path: str
    original_filename: str
    public_url: str
    def __init__(self, s3_path: _Optional[str] = ..., original_filename: _Optional[str] = ..., public_url: _Optional[str] = ...) -> None: ...

class AudioToPlay(_message.Message):
    __slots__ = ("s3_path", "original_filename", "public_url")
    S3_PATH_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_FILENAME_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_URL_FIELD_NUMBER: _ClassVar[int]
    s3_path: str
    original_filename: str
    public_url: str
    def __init__(self, s3_path: _Optional[str] = ..., original_filename: _Optional[str] = ..., public_url: _Optional[str] = ...) -> None: ...

class RulesReferences(_message.Message):
    __slots__ = ("sms", "handoff", "attributes", "globalFunctions", "variables")
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
    GLOBALFUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    sms: _containers.ScalarMap[str, bool]
    handoff: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    globalFunctions: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, sms: _Optional[_Mapping[str, bool]] = ..., handoff: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., globalFunctions: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Rules(_message.Message):
    __slots__ = ("behaviour", "references", "created_at", "created_by", "updated_at", "updated_by")
    BEHAVIOUR_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    behaviour: str
    references: RulesReferences
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, behaviour: _Optional[str] = ..., references: _Optional[_Union[RulesReferences, _Mapping]] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Rules_UpdateRules(_message.Message):
    __slots__ = ("behaviour", "references")
    BEHAVIOUR_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    behaviour: str
    references: RulesReferences
    def __init__(self, behaviour: _Optional[str] = ..., references: _Optional[_Union[RulesReferences, _Mapping]] = ...) -> None: ...

class LanguageBehaviorReferences(_message.Message):
    __slots__ = ("sms", "handoff", "attributes", "globalFunctions", "variables")
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
    GLOBALFUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    sms: _containers.ScalarMap[str, bool]
    handoff: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    globalFunctions: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, sms: _Optional[_Mapping[str, bool]] = ..., handoff: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., globalFunctions: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class LanguageBehavior(_message.Message):
    __slots__ = ("behavior_prompt", "language_code", "created_at", "created_by", "updated_at", "updated_by", "references")
    BEHAVIOR_PROMPT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    behavior_prompt: str
    language_code: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    references: LanguageBehaviorReferences
    def __init__(self, behavior_prompt: _Optional[str] = ..., language_code: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., references: _Optional[_Union[LanguageBehaviorReferences, _Mapping]] = ...) -> None: ...

class LanguageBehavior_UpdateLanguageBehavior(_message.Message):
    __slots__ = ("language_code", "behavior_prompt", "references")
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOR_PROMPT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    language_code: str
    behavior_prompt: str
    references: LanguageBehaviorReferences
    def __init__(self, language_code: _Optional[str] = ..., behavior_prompt: _Optional[str] = ..., references: _Optional[_Union[LanguageBehaviorReferences, _Mapping]] = ...) -> None: ...

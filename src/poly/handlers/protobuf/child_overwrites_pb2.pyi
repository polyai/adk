from poly.handlers.protobuf import knowledge_base_pb2 as _knowledge_base_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ChildOverwrites(_message.Message):
    __slots__ = ("knowledge_base",)
    KNOWLEDGE_BASE_FIELD_NUMBER: _ClassVar[int]
    knowledge_base: _knowledge_base_pb2.KnowledgeBase
    def __init__(self, knowledge_base: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase, _Mapping]] = ...) -> None: ...

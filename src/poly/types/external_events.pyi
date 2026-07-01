# Copyright PolyAI Limited
__all__ = ["ExternalEvents", "SMSReceived"]

import abc
from dataclasses import dataclass

class Event(abc.ABC): ...

@dataclass
class GenericExternalEvent(Event):
    ext_event_id: str
    send_to_llm: bool
    created_at: str | None = ...
    data: str | None = ...
    content_type: str | None = ...
    @classmethod
    def from_dict(cls, d: dict): ...

@dataclass
class SMSReceived(Event):
    from_number: str
    to_number: str
    text: str

class ExternalEvents:
    def __init__(self, sms_received: list[SMSReceived]) -> None: ...
    def listen_for_sms_next_turn(self, timeout: float = 20) -> None: ...
    def get_sms_received_history(self) -> list[SMSReceived]: ...

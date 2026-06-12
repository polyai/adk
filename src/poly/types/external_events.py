# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import abc


__all__ = ["Event", "GenericExternalEvent", "SMSReceived", "ExternalEvents"]


class Event(abc.ABC):
    """Base class for all event types."""


class GenericExternalEvent(Event):
    """A generic external event represented as a dictionary."""

    ext_event_id: str
    send_to_llm: bool
    created_at: str | None
    data: str | None
    content_type: str | None

    def __init__(
        self,
        ext_event_id: str,
        send_to_llm: bool,
        created_at: str | None = ...,
        data: str | None = ...,
        content_type: str | None = ...,
    ) -> None: ...
    @classmethod
    def from_dict(cls, d: dict):
        """from_dict"""


class SMSReceived(Event):
    """An SMS message received."""

    from_number: str
    to_number: str
    text: str

    def __init__(self, from_number: str, to_number: str, text: str) -> None: ...


class ExternalEvents:
    """Listen for events that are external to the agent, for example webhooks or"""

    def __init__(self, sms_received: list[SMSReceived]) -> None: ...
    def listen_for_sms_next_turn(self, timeout: float = ...) -> None:
        """listen for SMS in the next turn."""

    def get_sms_received_history(self) -> list[SMSReceived]:
        """Get the history of received SMS messages during the conversation."""

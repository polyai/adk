# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["ExternalEvents", "SMSReceived"]


class SMSReceived:
    """An SMS message received."""

    from_number: str
    to_number: str
    text: str

    def __init__(self, from_number: str, to_number: str, text: str) -> None: ...


class ExternalEvents:
    """Listen for events that are external to the agent, for example webhooks or
    incoming SMS messages.
    """

    def __init__(self, sms_received: list[SMSReceived]) -> None: ...
    def listen_for_sms_next_turn(self, timeout: float = ...) -> None: ...
    def get_sms_received_history(self) -> list[SMSReceived]: ...

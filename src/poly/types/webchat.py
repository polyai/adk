# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


__all__ = ["ChatCallAction", "WebchatInterface"]


class ChatCallAction:
    """A chat call action for an Agent Response."""

    def __init__(self, contact_number: str, title: str | None = ...): ...
    def to_dict(self):
        """Convert the ChatCallAction to a dictionary."""


class WebchatInterface:
    """Webchat-specific methods and properties for the conversation."""

    def __init__(self) -> None: ...
    @property
    def chat_call_actions(self) -> list[ChatCallAction]:
        """List of chat call actions for the next agent message."""

    def set_chat_call_actions(self, actions: list[ChatCallAction]) -> None:
        """Sets chat call actions for the agent message."""

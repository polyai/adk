# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any


class ChatCallAction:
    contact_number: Any
    title: Any

    def __init__(self, contact_number: str, title: str | None = None) -> None: ...
    def to_dict(self): ...


class WebchatInterface:
    def __init__(self) -> None: ...
    @property
    def chat_call_actions(self) -> list[ChatCallAction]: ...
    def set_chat_call_actions(self, actions: list[ChatCallAction]) -> None: ...

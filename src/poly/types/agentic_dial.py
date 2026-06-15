# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any
from collections.abc import Iterator


@dataclass
class Destination:
    name: str
    phone_number: str
    sip_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> Destination: ...
    def to_dict(self) -> dict: ...


@dataclass
class AgenticDialConfig:
    destinations: list[Destination] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> AgenticDialConfig: ...


@dataclass
class AgenticDialData:
    config: AgenticDialConfig = field(default_factory=AgenticDialConfig)
    active_dial_destinations: list[str] = field(default_factory=list)
    dial_id: str | None = ...

    @classmethod
    def from_dict(cls, data: dict) -> AgenticDialData: ...


@dataclass
class MessageToParent:
    content: str


@dataclass
class MessageToChild:
    destination: str
    content: str


class Destinations:
    def __init__(self, destinations: list[Destination]) -> None: ...
    def __iter__(self) -> Iterator[Destination]: ...
    def __getitem__(self, name: str) -> Destination: ...
    def add(
        self, *, name: str, phone_number: str, sip_headers: dict[str, str] | None = None
    ) -> None: ...
    def clear(self) -> None: ...


class AgenticDial:
    destinations: Any

    def __init__(self, data: AgenticDialData | None) -> None: ...
    @property
    def active_destinations(self) -> list[str]: ...
    def send_to_parent(self, content: str) -> None: ...
    def send_to_child(self, destination: str, content: str) -> None: ...

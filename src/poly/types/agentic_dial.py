# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from collections.abc import Iterator


__all__ = [
    "Destination",
    "AgenticDialConfig",
    "AgenticDialData",
    "MessageToParent",
    "MessageToChild",
    "Destinations",
    "AgenticDial",
]


class Destination:
    """Agentic dial destination configuration"""

    name: str
    phone_number: str
    sip_headers: dict[str, str]

    def __init__(self, name: str, phone_number: str, sip_headers: dict[str, str] = ...) -> None: ...
    @classmethod
    def from_dict(cls, data: dict) -> Destination:
        """Create a Destination from a dictionary."""

    def to_dict(self) -> dict:
        """Convert to a dictionary."""


class AgenticDialConfig:
    """Agentic dial configuration"""

    destinations: list[Destination]

    def __init__(self, destinations: list[Destination] = ...) -> None: ...
    @classmethod
    def from_dict(cls, data: dict) -> AgenticDialConfig:
        """Create an AgenticDialConfig from a dictionary."""


class AgenticDialData:
    """Agentic dial runtime data."""

    config: AgenticDialConfig
    active_dial_destinations: list[str]
    dial_id: str | None

    def __init__(
        self,
        config: AgenticDialConfig = ...,
        active_dial_destinations: list[str] = ...,
        dial_id: str | None = ...,
    ) -> None: ...
    @classmethod
    def from_dict(cls, data: dict) -> AgenticDialData:
        """Create an AgenticDialData from a dictionary."""


class MessageToParent:
    """A message to send to the parent agent."""

    content: str

    def __init__(self, content: str) -> None: ...


class MessageToChild:
    """A message to send to a child agent."""

    destination: str
    content: str

    def __init__(self, destination: str, content: str) -> None: ...


class Destinations:
    """Manages a collection of agentic dial destinations."""

    def __init__(self, destinations: list[Destination]): ...
    def __iter__(self) -> Iterator[Destination]:
        """Iterate over all destinations."""

    def __getitem__(self, name: str) -> Destination:
        """Get a destination by name."""

    def add(
        self, *, name: str, phone_number: str, sip_headers: dict[str, str] | None = ...
    ) -> None:
        """Add a single destination."""

    def clear(self) -> None:
        """Clear all destinations."""


class AgenticDial:
    """Manages agentic dial functionality."""

    def __init__(self, data: AgenticDialData | None): ...
    @property
    def active_destinations(self) -> list[str]:
        """List of active destination names, i.e. those that have been dialed."""

    def send_to_parent(self, content: str) -> None:
        """Send a message to the parent agent."""

    def send_to_child(self, destination: str, content: str) -> None:
        """Send a message to a child agent."""

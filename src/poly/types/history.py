# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


__all__ = ["UserInput", "AgentResponse"]


class UserInput:
    """Object representing a user turn"""

    def __init__(self, text: str):
        """Initialize a UserInput event."""

    @property
    def text(self) -> str:
        """The user's input text."""

    @property
    def role(self) -> str:
        """The role of the event."""

    def __repr__(self) -> str:
        """User-friendly representation of the object"""

    def __eq__(self, other):
        """Check equality based on text attribute."""

    def to_dict(self) -> dict[str, str]:
        """Convert the event to dictionary format"""

    def to_string(self) -> str:
        """Convert the object into a user-friendly string"""


class AgentResponse:
    """Object representing an agent turn"""

    def __init__(self, text: str):
        """Initialize an AgentResponse event."""

    @property
    def text(self) -> str:
        """The agent's response text."""

    @property
    def role(self) -> str:
        """The role of the event."""

    def __repr__(self) -> str:
        """User-friendly representation of the object"""

    def __eq__(self, other):
        """Check equality based on text attribute."""

    def to_dict(self) -> dict[str, str]:
        """Convert the event to dictionary format"""

    def to_string(self) -> str:
        """User-friendly format for display"""

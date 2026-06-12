# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from typing import Any
from .conversation import Conversation


__all__ = ["Transition", "StepTransition", "FlowFunctionExecutor", "Flow"]


class Transition:
    """A flow transition triggered by a function"""

    exit_flow: bool
    goto_flow: str | None
    goto_step: str | None

    def __init__(
        self, exit_flow: bool = ..., goto_flow: str | None = ..., goto_step: str | None = ...
    ) -> None: ...
    @classmethod
    def from_dict(cls, d: dict) -> Transition:
        """Construct from dict"""

    def is_noop(self) -> bool:
        """Check if this transition does nothing"""


class StepTransition:
    """Mutable object to trigger step transitions"""

    goto_step: str | None

    def __init__(self, goto_step: str | None = ...) -> None: ...


class FlowFunctionExecutor(dict):
    """Flow function executor"""

    def __init__(self, conv: Conversation, flow: Flow): ...
    def __getattr__(self, name: str) -> Any:
        """Dynamically import and return a function when accessed via dot notation."""


class Flow:
    """Object for working within flows"""

    def __init__(
        self,
        current_step: str,
        step_transition: StepTransition,
        conv: Conversation,
        function_dir: str,
    ):
        """init"""

    @property
    def current_step(self) -> str:
        """The name of the step we're currently in"""

    @property
    def functions(self) -> FlowFunctionExecutor:
        """The functions available to the flow"""

    def goto_step(self, step_name: str, label: str | None = ...):
        """Trigger a transition to a different step"""

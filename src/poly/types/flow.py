# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from .conversation import Conversation as Conversation
from typing import Any


@dataclass
class Transition:
    exit_flow: bool = ...
    goto_flow: str | None = ...
    goto_step: str | None = ...

    @classmethod
    def from_dict(cls, d: dict) -> Transition: ...
    def is_noop(self) -> bool: ...


@dataclass
class StepTransition:
    goto_step: str | None = ...


class FlowFunctionExecutor(dict):
    conv: Any
    flow: Any

    def __init__(self, conv: Conversation, flow: Flow) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


class Flow:
    function_dir: Any

    def __init__(
        self,
        current_step: str,
        step_transition: StepTransition,
        conv: Conversation,
        function_dir: str,
    ) -> None: ...
    @property
    def current_step(self) -> str: ...
    @property
    def functions(self) -> FlowFunctionExecutor: ...
    def goto_step(self, step_name: str, label: str | None = None): ...

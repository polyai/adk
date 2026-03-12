# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any

from .conversation import Conversation

__all__ = ["Flow", "FlowFunctionExecutor"]


class FlowFunctionExecutor(dict):
    """Flow function executor for importing functions from the flow's functions directory."""

    def __init__(self, conv: Conversation, flow: Flow) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


class Flow:
    """Object for working within flows"""

    function_dir: str

    def __init__(
        self,
        current_step: str,
        step_transition: Any,
        conv: Conversation,
        function_dir: str,
    ) -> None: ...
    @property
    def current_step(self) -> str: ...
    @property
    def functions(self) -> FlowFunctionExecutor: ...
    def goto_step(self, step_name: str, label: str | None = ...) -> None: ...

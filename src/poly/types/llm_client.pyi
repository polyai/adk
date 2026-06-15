# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from dataclasses import dataclass
from typing import Literal

class ChatCompletionError(Exception):
    def __init__(self, message: str) -> None: ...

@dataclass
class _InferenceConfig:
    temperature: int | None = ...
    top_p: float | None = ...
    max_tokens: int | None = ...
    response_format: dict | None = ...

@dataclass
class _ModelPromptEvent:
    content: str
    type: Literal["prompt"] = ...

@dataclass
class _ChatCompletionRequest:
    provider_model_id: str
    model_config: dict
    inference_config: _InferenceConfig
    events: list[_ModelPromptEvent]

@dataclass
class _ChatCompletionResponse:
    content: str

class _LLMClient:
    def __init__(
        self,
        account_id: str,
        project_id: str,
        client_env: str,
        conversation_id: str,
        correlation_id: str | None = None,
        base_url: str = "https://api.internal.polyai.app",
        timeout: int = 8,
    ) -> None: ...
    def chat_completion(self, request: _ChatCompletionRequest) -> _ChatCompletionResponse: ...

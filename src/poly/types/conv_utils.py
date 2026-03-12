# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any, Literal

from runtime.value_extraction import Address

__all__ = ["Utils"]


class Utils:
    """Utility class for the conv object."""

    def __init__(
        self,
        account_id: str,
        project_id: str,
        client_env: str,
        conversation_id: str,
        turn_index: int,
        language: str,
        history: list[Any],
        transcript_alternatives: list[str],
        vpc_enabled: bool = ...,
        correlation_id: str | None = ...,
    ) -> None: ...
    def extract_address(
        self,
        addresses: list[Address] | None = ...,
        country: str = ...,
    ) -> Address: ...
    def extract_city(
        self,
        city_spellings: list[str] | None = ...,
        states: list[str] | None = ...,
        country: str = ...,
    ) -> Address: ...
    def prompt_llm(
        self,
        prompt: str,
        *,
        show_history: bool = ...,
        return_json: bool = ...,
        model: Literal["gpt-4o", "claude-sonnet-4"] = ...,
    ) -> str | dict: ...
    def get_secret(self, secret_name: str) -> str | dict: ...

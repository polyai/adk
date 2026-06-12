# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from typing import Literal
import runtime.value_extraction_types as extraction_types
from runtime.history import AgentResponse, UserInput
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
        history: list[UserInput | AgentResponse],
        transcript_alternatives: list[str],
        vpc_enabled: bool = ...,
        correlation_id: str | None = ...,
    ): ...
    def extract_address(self, addresses: list[Address] | None = ..., country: str = ...) -> Address:
        """[Opt-in Feature] 🚧"""

    def extract_city(
        self,
        city_spellings: list[str] | None = ...,
        states: list[str] | None = ...,
        country: str = ...,
    ) -> Address:
        """[Opt-in Feature] 🚧"""

    def prompt_llm(
        self,
        prompt: str,
        *,
        show_history: bool = ...,
        return_json: bool = ...,
        model: Literal[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-5-chat",
            "claude-sonnet-4",
            "claude-3.5-haiku",
        ] = ...,
    ) -> str | dict:
        """[Opt-in Feature] 🚧"""

    def validate_entity(
        self, value: str, entity_config: extraction_types.EntityConfig
    ) -> _EntityValidationResponse:
        """Validate an entity value against its configuration."""

    def get_secret(self, secret_name: str) -> str | dict:
        """Get secret value"""

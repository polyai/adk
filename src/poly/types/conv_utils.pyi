# Copyright PolyAI Limited
__all__ = ["Utils"]

from . import value_extraction_types as extraction_types
from .history import AgentResponse as AgentResponse, UserInput as UserInput
from .value_extraction import Address as Address, _EntityValidationResponse
from typing import Any, Literal

class Utils:
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
        vpc_enabled: bool = False,
        correlation_id: str | None = None,
    ) -> None: ...
    EntityType: Any
    NumericType: Any
    NumericConfig: Any
    QuantityConfig: Any
    CurrencyConfig: Any
    NameConfig: Any
    FreeTextConfig: Any
    AlphanumericConfig: Any
    DateConfig: Any
    EmailConfig: Any
    TimeConfig: Any
    PhoneNumberConfig: Any
    EnumConfig: Any
    EntityConfig: Any
    def extract_address(
        self, addresses: list[Address] | None = None, country: str = "US"
    ) -> Address: ...
    def extract_city(
        self,
        city_spellings: list[str] | None = None,
        states: list[str] | None = None,
        country: str = "US",
    ) -> Address: ...
    def prompt_llm(
        self,
        prompt: str,
        *,
        show_history: bool = False,
        return_json: bool = False,
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
        ] = "gpt-4o",
    ) -> str | dict: ...
    def validate_entity(
        self, value: str, entity_config: extraction_types.EntityConfig
    ) -> _EntityValidationResponse: ...
    def get_secret(self, secret_name: str) -> str | dict: ...

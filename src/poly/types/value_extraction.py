# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from .value_extraction_types import EntityConfig as EntityConfig


class ExtractionError(Exception):
    def __init__(self, message: str) -> None: ...


@dataclass
class Address:
    street_number: str | None = ...
    street_name: str | None = ...
    city: str | None = ...
    state: str | None = ...
    postcode: str | None = ...
    country: str | None = ...


@dataclass
class _AddressExtractionRequest:
    hypotheses: list[str]
    country: str = ...
    language: str = ...
    addresses: list[Address] | None = ...
    states: list[str] | None = ...
    spellings: list[str] | None = ...


@dataclass
class _AddressExtractionResponse:
    address: Address
    extraction_info: str


@dataclass
class _EntityValidationRequest:
    value: str
    entity_config: EntityConfig


@dataclass
class _EntityValidationResponse:
    is_valid: bool
    message: str | None = ...


class _ValueExtractionClient:
    def __init__(
        self,
        account_id: str,
        project_id: str,
        client_env: str,
        conversation_id: str,
        turn_index: int,
        correlation_id: str | None = None,
        base_url: str = "https://api.internal.polyai.app",
        timeout: int = 8,
    ) -> None: ...
    def extract_address(self, request: _AddressExtractionRequest) -> _AddressExtractionResponse: ...
    def extract_city(self, request: _AddressExtractionRequest) -> _AddressExtractionResponse: ...
    def validate_entity(self, request: _EntityValidationRequest) -> _EntityValidationResponse: ...

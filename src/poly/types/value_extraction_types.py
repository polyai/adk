# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import re
from datetime import date, time
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel


__all__ = [
    "EntityType",
    "NumericType",
    "BaseRangeConfig",
    "NonNegativeMaxRangeConfig",
    "NumericConfig",
    "QuantityConfig",
    "CurrencyConfig",
    "NameConfig",
    "FreeTextConfig",
    "AlphanumericConfig",
    "DateConfig",
    "EmailConfig",
    "TimeConfig",
    "PhoneNumberConfig",
    "EnumConfig",
    "EntityConfig",
]


class EntityType(StrEnum):
    """Enum for entity types."""


class NumericType(StrEnum):
    """Enum for supported numeric types"""


class BaseRangeConfig(BaseModel):
    """Base config with min/max validation."""

    min_inclusive: float | None
    max_inclusive: float | None


class NonNegativeMaxRangeConfig(BaseRangeConfig):
    """Base config with non-negative min/max validation"""

    def validate_max(cls, v):
        """Validates that max value is non-negative"""


class NumericConfig(BaseRangeConfig):
    """Configuration for numeric entities."""

    entity_type: Literal["numeric"]
    numeric_type: NumericType

    def validate_min_max(cls, v, values):
        """Validate that min is not greater than max."""


class QuantityConfig(NonNegativeMaxRangeConfig):
    """Configuration for quantity entities."""

    entity_type: Literal["quantity"]
    min_inclusive: int | None
    max_inclusive: int | None
    numeric_type: NumericType


class CurrencyConfig(NonNegativeMaxRangeConfig):
    """Configuration for currency entities."""

    entity_type: Literal["currency"]
    min_inclusive: float | None
    max_inclusive: float | None
    numeric_type: NumericType


class NameConfig(BaseModel):
    """Configuration for name entities."""

    entity_type: Literal["name"]


class FreeTextConfig(BaseModel):
    """Configuration for free text entities."""

    entity_type: Literal["free_text"]


class AlphanumericConfig(BaseModel):
    """Configuration for alphanumeric entities."""

    custom_regex: str
    entity_type: Literal["alphanumeric"]
    capturing_group: int | None

    def validate_regex(cls, v):
        """Validate and compile the regex pattern."""

    def validate_capturing_group(cls, v):
        """Validate capturing group."""

    def get_compiled_regex(self) -> re.Pattern:
        """Get the compiled regex pattern."""


class DateConfig(BaseModel):
    """Configuration for date entities."""

    entity_type: Literal["date"]
    day_first: bool | None
    earliest_date_inclusive: date | None
    latest_date_inclusive: date | None

    def parse_dates(cls, v, values):
        """Parse date strings into date objects."""

    def validate_dates(cls, v, values):
        """Validate that earliest date is not after latest date."""


class EmailConfig(AlphanumericConfig):
    """Configuration for email entities."""

    custom_regex: str
    entity_type: Literal["email"]
    capturing_group: int | None


class TimeConfig(BaseModel):
    """Configuration for time entities."""

    entity_type: Literal["time"]
    format: str
    earliest_time_inclusive: time | None
    latest_time_inclusive: time | None
    time_pivot: int

    def parse_times(cls, v, values):
        """Parse time strings into time objects."""

    def validate_times(cls, v, values):
        """Validate that earliest time is not after latest time."""

    def validate_time_pivot(cls, v, values):
        """Validate that a time pivot, if provided is within a 12 hour range"""


class PhoneNumberConfig(BaseModel):
    """Configuration for phone number entities."""

    entity_type: Literal["phone_number"]
    regions: set[str] | None

    def validate_regions(cls, v):
        """Clean and validate region codes."""


class EnumConfig(BaseModel):
    """Configuration for Enum entities"""

    entity_type: Literal["enum"]
    allowed_vals: set[str] | None

    def validate_allowed_vals(cls, v):
        """Clean and validate allowed values."""


EntityConfig = (
    NumericConfig
    | QuantityConfig
    | CurrencyConfig
    | NameConfig
    | FreeTextConfig
    | AlphanumericConfig
    | DateConfig
    | EmailConfig
    | TimeConfig
    | PhoneNumberConfig
    | EnumConfig
)

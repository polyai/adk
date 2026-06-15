# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
import re
from datetime import date, time
from enum import StrEnum
from pydantic import BaseModel
from typing import Literal


class EntityType(StrEnum):
    ADDRESS = "address"
    ALPHANUMERIC = "alphanumeric"
    DATE = "date"
    EMAIL = "email"
    NUMERIC = "numeric"
    PHONE_NUMBER = "phone_number"
    TIME = "time"
    ENUM = "enum"
    CURRENCY = "currency"
    QUANTITY = "quantity"
    NAME = "name"
    FREE_TEXT = "free_text"


class NumericType(StrEnum):
    INT = "int"
    FLOAT = "float"


class BaseRangeConfig(BaseModel):
    min_inclusive: float | None
    max_inclusive: float | None


class NonNegativeMaxRangeConfig(BaseRangeConfig):
    def validate_max(cls, v): ...


class NumericConfig(BaseRangeConfig):
    entity_type: Literal["numeric"]
    numeric_type: NumericType

    def validate_min_max(cls, v, values): ...


class QuantityConfig(NonNegativeMaxRangeConfig):
    entity_type: Literal["quantity"]
    min_inclusive: int | None
    max_inclusive: int | None
    numeric_type: NumericType


class CurrencyConfig(NonNegativeMaxRangeConfig):
    entity_type: Literal["currency"]
    min_inclusive: float | None
    max_inclusive: float | None
    numeric_type: NumericType


class NameConfig(BaseModel):
    entity_type: Literal["name"]


class FreeTextConfig(BaseModel):
    entity_type: Literal["free_text"]


class AlphanumericConfig(BaseModel):
    custom_regex: str
    entity_type: Literal["alphanumeric"]
    capturing_group: int | None

    def validate_regex(cls, v): ...
    def validate_capturing_group(cls, v): ...
    def get_compiled_regex(self) -> re.Pattern: ...


class DateConfig(BaseModel):
    entity_type: Literal["date"]
    day_first: bool | None
    earliest_date_inclusive: date | None
    latest_date_inclusive: date | None

    def parse_dates(cls, v, values): ...
    def validate_dates(cls, v, values): ...


class EmailConfig(AlphanumericConfig):
    custom_regex: str
    entity_type: Literal["email"]
    capturing_group: int | None


class TimeConfig(BaseModel):
    entity_type: Literal["time"]
    format: str
    earliest_time_inclusive: time | None
    latest_time_inclusive: time | None
    time_pivot: int

    def parse_times(cls, v, values): ...
    def validate_times(cls, v, values): ...
    def validate_time_pivot(cls, v, values): ...


class PhoneNumberConfig(BaseModel):
    entity_type: Literal["phone_number"]
    regions: set[str] | None

    def validate_regions(cls, v): ...


class EnumConfig(BaseModel):
    entity_type: Literal["enum"]
    allowed_vals: set[str] | None

    def validate_allowed_vals(cls, v): ...


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

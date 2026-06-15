# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from dataclasses import dataclass

@dataclass
class APIRequestMetadata:
    url: str
    method: str
    response_time: float
    status_code: int
    error: dict = ...

    def to_json_str(self) -> str: ...

@dataclass
class AnalyticsEvent:
    name: str
    value: str
    timestamp_str: str = ...

    def __post_init__(self) -> None: ...
    @classmethod
    def from_dict(cls, data: dict) -> AnalyticsEvent: ...

def response_to_analytics_events(response: list[dict]) -> list[AnalyticsEvent]: ...

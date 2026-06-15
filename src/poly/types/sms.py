# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = [
    "OutgoingSMS",
    "OutgoingSMSTemplate",
    "SMSClientFailure",
    "SMSCredentials",
    "SMSTemplate",
]

from collections.abc import Callable as Callable
from dataclasses import dataclass
from requests import Response as Response
from typing import Any, Protocol


class SMSClientFailure(Exception):
    def __init__(self, integration: str, reason: str) -> None: ...


@dataclass
class SMSCredentials:
    account_sid: str
    auth_token: str


@dataclass
class SMSTemplate:
    name: str
    content: str
    phone_number: str


@dataclass
class OutgoingSMSTemplate:
    to_number: str
    template: str


@dataclass
class OutgoingSMS:
    to_number: str
    from_number: str
    content: str
    content_id: str | None = ...


SMSObj = OutgoingSMS | OutgoingSMSTemplate


def parse_sms_dict(d: dict) -> SMSObj: ...


@dataclass
class SMSSentEvent:
    success: bool
    sms: SMSObj

    @classmethod
    def from_dict(cls, d) -> SMSSentEvent: ...
    def to_dict(self) -> dict: ...


def fibonacci_backoff(n: int): ...


class SMSClient(Protocol):
    def send_sms(self, sms: OutgoingSMS) -> dict: ...
    def retry_send_sms(self, sms: OutgoingSMS, retry_count: int) -> dict: ...


class TwilioSMSClient(SMSClient):
    sms_credentials: Any

    def __init__(self, sms_credentials: SMSCredentials) -> None: ...
    def send_content_template(self, sms: OutgoingSMS, **kwargs) -> dict: ...
    def send_sms(self, sms: OutgoingSMS) -> dict: ...
    def retry_send_sms(self, sms: OutgoingSMS, retry_count: int): ...
    def retry_send_content_template(self, sms: OutgoingSMS, retry_count: int, **kwargs): ...


class TelnyxSMSClient(SMSClient):
    sms_credentials: Any

    def __init__(self, sms_credentials: SMSCredentials) -> None: ...
    def send_sms(self, sms: OutgoingSMS) -> dict: ...
    def retry_send_sms(self, sms: OutgoingSMS, retry_count: int) -> dict: ...

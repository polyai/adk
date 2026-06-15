# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["InvalidInput", "MissingAccess", "SecretNotFound"]

from typing import Any

secret_client: Any


class SecretNotFound(Exception):
    def __init__(self, secret_name: str) -> None: ...


class MissingAccess(Exception):
    def __init__(self, assistant_id: str, secret_name: str) -> None: ...


class InvalidInput(Exception):
    def __init__(self, assistant_id: str, secret_name: str) -> None: ...


class InternalError(Exception):
    def __init__(self) -> None: ...


def secret_vault(secret_name: str) -> str | dict: ...
def get_secret_vault_custom_secret(secret_name: str) -> dict: ...
def build_sms_secret_name() -> str: ...

# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations


class JanusSMSError(Exception):
    def __init__(self, message: str) -> None: ...


def send_sms_via_janus(
    account_id: str,
    from_number: str,
    to_number: str,
    body: str,
    base_url: str = "https://api.internal.polyai.app",
    timeout: int = 8,
) -> str: ...

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


class SMSClientFailure(Exception):
    """SMS Client Failure"""

    def __init__(self, integration: str, reason: str) -> None: ...


class SMSCredentials:
    """SMS credentials"""

    account_sid: str
    auth_token: str

    def __init__(self, account_sid: str, auth_token: str) -> None: ...


class SMSTemplate:
    """SMS template"""

    name: str
    content: str
    phone_number: str

    def __init__(self, name: str, content: str, phone_number: str) -> None: ...


class OutgoingSMSTemplate:
    """SMS template to send"""

    to_number: str
    template: str

    def __init__(self, to_number: str, template: str) -> None: ...


class OutgoingSMS:
    """SMS to send"""

    to_number: str
    from_number: str
    content: str
    content_id: str | None

    def __init__(
        self,
        to_number: str,
        from_number: str,
        content: str,
        content_id: str | None = ...,
    ) -> None: ...

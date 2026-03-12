# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["InvalidInput", "MissingAccess", "SecretNotFound"]


class SecretNotFound(Exception):
    """Secret with specified name cannot be found"""

    def __init__(self, secret_name: str) -> None: ...


class MissingAccess(Exception):
    """Assistant is not on access list for the secret"""

    def __init__(self, assistant_id: str, secret_name: str) -> None: ...


class InvalidInput(Exception):
    """Assistant is sending invalid input for secret access"""

    def __init__(self, assistant_id: str, secret_name: str) -> None: ...

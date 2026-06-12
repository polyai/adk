# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


__all__ = ["ExtractionError", "Address"]


class ExtractionError(Exception):
    """Error in retrieving extracted values from the conversation."""

    def __init__(self, message: str): ...


class Address:
    """Represents a structured address."""

    street_number: str | None
    street_name: str | None
    city: str | None
    state: str | None
    postcode: str | None
    country: str | None

    def __init__(
        self,
        street_number: str | None = ...,
        street_name: str | None = ...,
        city: str | None = ...,
        state: str | None = ...,
        postcode: str | None = ...,
        country: str | None = ...,
    ) -> None: ...

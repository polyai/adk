# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["Address"]


class Address:
    """
    Represents a structured address.

    Attributes:
        street_number: The street number.
        street_name: The street name.
        city: The city name.
        state: The state name.
        postcode: The zip code or postal code.
        country: The country name.
    """

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

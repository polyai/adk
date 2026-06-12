# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any

from ..integration import Integration

__all__ = ["Tripleseat"]


class Tripleseat(Integration):
    """Tripleseat integration class for proxying requests to the Tripleseat API"""

    integration_id: str
    integration_name: str

    def get_bookings(self) -> Any:
        """Get bookings from Tripleseat."""

    def create_lead(
        self,
        public_key: str,
        first_name: str | None = ...,
        last_name: str | None = ...,
        email_address: str | None = ...,
        phone_number: str | None = ...,
        location_id: str | None = ...,
        additional_fields: dict | None = ...,
    ) -> Any:
        """Create a lead in Tripleseat."""

# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from ..integration import Integration
import requests


__all__ = ["Tripleseat"]


class Tripleseat(Integration):
    """Tripleseat integration class for proxying requests to the Tripleseat API with"""

    def get_bookings(self) -> requests.Response:
        """Example method for getting bookings from Tripleseat"""

    def create_lead(
        self,
        public_key: str,
        first_name: str | None = ...,
        last_name: str | None = ...,
        email_address: str | None = ...,
        phone_number: str | None = ...,
        location_id: str | None = ...,
        additional_fields: dict | None = ...,
    ) -> requests.Response:
        """Create a lead in Tripleseat using the proxy request method"""

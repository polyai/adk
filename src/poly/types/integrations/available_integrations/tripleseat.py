# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["Tripleseat"]

import requests
from ..integration import Integration


class Tripleseat(Integration):
    integration_id: str
    integration_name: str

    def get_bookings(self) -> requests.Response: ...
    def create_lead(
        self,
        public_key: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email_address: str | None = None,
        phone_number: str | None = None,
        location_id: str | None = None,
        additional_fields: dict | None = None,
    ) -> requests.Response: ...

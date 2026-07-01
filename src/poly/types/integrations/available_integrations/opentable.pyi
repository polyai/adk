# Copyright PolyAI Limited
__all__ = ["OpenTable"]

import requests
from ..integration import Integration

BASE_OPENTABLE_API_URL: str
V1_BASE_OPENTABLE_API_URL_SUFFIX: str
V2_BASE_OPENTABLE_API_URL_SUFFIX: str
OPENTABLE_AUTH_URL: str
OPENTABLE_SECRET_NAME: str

class OpenTable(Integration):
    integration_id: str
    integration_name: str
    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, any] | None = None,
        timeout: int = ...,
    ) -> requests.Response: ...
    def check_availability(
        self,
        restaurant_id: str,
        party_size: int,
        start_date_time: str,
        forward_minutes: int | None = None,
        backward_minutes: int | None = None,
        include_experiences: bool = False,
    ) -> requests.Response: ...
    def lock_slot(
        self,
        restaurant_id: int,
        party_size: int,
        date_time: str,
        table_type: str = "default",
        dining_area_id: int | None = None,
        experience_id: int | None = None,
    ) -> requests.Response: ...
    def make_reservation(
        self,
        restaurant_id: str,
        reservation_token: str,
        first_name: str,
        last_name: str,
        phone_number: str,
        phone_country_code: int = 1,
        special_request: str | None = None,
        sms_notifications_opt_in: bool = True,
        table_type: str = "default",
        dining_area_id: int | None = None,
        payments: dict | None = None,
    ) -> requests.Response: ...
    def lookup_bookings(
        self, restaurant_id: str, phone_number: str, phone_country_code: int = 1
    ) -> requests.Response: ...
    def update_reservation(
        self,
        restaurant_id: str,
        reservation_id: str,
        party_size: int | None = None,
        date_time: str | None = None,
        special_request: str | None = None,
    ) -> requests.Response: ...
    def cancel_booking(self, restaurant_id: str, reservation_id: str) -> requests.Response: ...
    def get_experiences(self, restaurant_id: str) -> requests.Response: ...
    def check_availability_v2(
        self,
        restaurant_id: str,
        party_size: int,
        start_date_time: str,
        forward_minutes: int | None = None,
        backward_minutes: int | None = None,
        require_attributes: str | None = None,
        include_credit_card_results: bool = False,
        include_experiences: bool = False,
    ) -> requests.Response: ...

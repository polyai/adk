"""Client for the public SIP Trunking API.

Copyright PolyAI Limited
"""

from typing import Any
from urllib.parse import quote

from poly.handlers.platform_api import PlatformAPIHandler


class SIPTrunkingAPIHandler:
    """Wrap the account-level SIP Trunking API."""

    _TRUNKS_URL = "/v1/accounts/{account_id}/telephony/sip-trunks"
    _TRUNK_URL = _TRUNKS_URL + "/{trunk_id}"
    _EXTENSIONS_URL = _TRUNK_URL + "/extensions"
    _EXTENSION_URL = _EXTENSIONS_URL + "/{extension}"

    @staticmethod
    def _path_part(value: str) -> str:
        """URL-encode a user-provided path segment."""
        return quote(value, safe="")

    @classmethod
    def list_trunks(cls, region: str, account_id: str) -> dict[str, Any]:
        endpoint = cls._TRUNKS_URL.format(account_id=cls._path_part(account_id))
        return PlatformAPIHandler.make_request(region, endpoint)

    @classmethod
    def create_trunk(cls, region: str, account_id: str, data: dict[str, Any]) -> dict[str, Any]:
        endpoint = cls._TRUNKS_URL.format(account_id=cls._path_part(account_id))
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

    @classmethod
    def get_trunk(cls, region: str, account_id: str, trunk_id: str) -> dict[str, Any]:
        endpoint = cls._TRUNK_URL.format(
            account_id=cls._path_part(account_id), trunk_id=cls._path_part(trunk_id)
        )
        return PlatformAPIHandler.make_request(region, endpoint)

    @classmethod
    def update_trunk(
        cls, region: str, account_id: str, trunk_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        endpoint = cls._TRUNK_URL.format(
            account_id=cls._path_part(account_id), trunk_id=cls._path_part(trunk_id)
        )
        return PlatformAPIHandler.make_request(region, endpoint, "PATCH", data=data)

    @classmethod
    def delete_trunk(cls, region: str, account_id: str, trunk_id: str) -> dict[str, Any]:
        endpoint = cls._TRUNK_URL.format(
            account_id=cls._path_part(account_id), trunk_id=cls._path_part(trunk_id)
        )
        return PlatformAPIHandler.make_request(region, endpoint, "DELETE")

    @classmethod
    def list_extensions(cls, region: str, account_id: str, trunk_id: str) -> dict[str, Any]:
        endpoint = cls._EXTENSIONS_URL.format(
            account_id=cls._path_part(account_id), trunk_id=cls._path_part(trunk_id)
        )
        return PlatformAPIHandler.make_request(region, endpoint)

    @classmethod
    def create_extension(
        cls,
        region: str,
        account_id: str,
        trunk_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        endpoint = cls._EXTENSIONS_URL.format(
            account_id=cls._path_part(account_id), trunk_id=cls._path_part(trunk_id)
        )
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

    @classmethod
    def get_extension(
        cls, region: str, account_id: str, trunk_id: str, extension: str
    ) -> dict[str, Any]:
        endpoint = cls._EXTENSION_URL.format(
            account_id=cls._path_part(account_id),
            trunk_id=cls._path_part(trunk_id),
            extension=cls._path_part(extension),
        )
        return PlatformAPIHandler.make_request(region, endpoint)

    @classmethod
    def update_extension(
        cls,
        region: str,
        account_id: str,
        trunk_id: str,
        extension: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        endpoint = cls._EXTENSION_URL.format(
            account_id=cls._path_part(account_id),
            trunk_id=cls._path_part(trunk_id),
            extension=cls._path_part(extension),
        )
        return PlatformAPIHandler.make_request(region, endpoint, "PATCH", data=data)

    @classmethod
    def delete_extension(
        cls, region: str, account_id: str, trunk_id: str, extension: str
    ) -> dict[str, Any]:
        endpoint = cls._EXTENSION_URL.format(
            account_id=cls._path_part(account_id),
            trunk_id=cls._path_part(trunk_id),
            extension=cls._path_part(extension),
        )
        return PlatformAPIHandler.make_request(region, endpoint, "DELETE")

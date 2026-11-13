"""Util functions for testing

Copyright PolyAI Limited
"""

import os
from contextlib import contextmanager
from typing import Optional
from unittest.mock import MagicMock, patch

import requests


def make_mock_response(status_code=200, json_body=None, content=b""):
    """Build a MagicMock that behaves like a requests.Response.

    Args:
        status_code (int): The HTTP status code exposed on ``.status_code``.
        json_body (Any | None): Value returned by ``.json()``. When ``None``,
            ``.json()`` raises ``requests.exceptions.JSONDecodeError`` to
            simulate a body that is not valid JSON.
        content (bytes): Raw bytes exposed on ``.content``.

    Returns:
        MagicMock: A mock response whose ``.raise_for_status()`` raises
            ``requests.HTTPError`` (with ``response`` set to the mock) when
            ``status_code`` is >= 400, and is a no-op otherwise.
    """
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.content = content
    response.text = content.decode(errors="replace") if content else ""

    if json_body is None:

        def _raise_json_error():
            raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)

        response.json.side_effect = _raise_json_error
    else:
        response.json.return_value = json_body

    def _raise_for_status():
        if status_code >= 400:
            raise requests.HTTPError(f"{status_code} Error", response=response)

    response.raise_for_status.side_effect = _raise_for_status
    return response


@contextmanager
def mock_read_from_file(content_or_file_map):
    """Context manager to mock Resource.read_from_file() method.

    Args:
        content_or_file_map (str | dict[str, str]):
            - If str: The content to return for all files.
            - If dict: Maps file paths to their content (file_path -> content).

    Usage:
        # Single content for all files:
        with mock_read_from_file("file content"):
            resource = SomeResource.read_local_resource(...)

        # Different content per file:
        with mock_read_from_file({
            "flows/test_flow/steps/test_step.yaml": "step content",
            "flows/test_flow/steps/other_step.yaml": "other content",
        }):
            resource = SomeResource.read_local_resource(...)
    """
    if isinstance(content_or_file_map, dict):
        # File-path based mocking
        def mock_read_side_effect(file_path, **kwargs):
            # Try exact match first
            if file_path in content_or_file_map:
                return content_or_file_map[file_path]
            # Try partial match (for cases where path might differ slightly)
            for path, content in content_or_file_map.items():
                if path in file_path or file_path in path:
                    return content
            # Default: do not mock the file
            with open(file_path) as f:
                return f.read()

        with patch(
            "poly.resources.resource.Resource.read_from_file",
            side_effect=mock_read_side_effect,
        ):
            yield
    else:
        # Single content for all files (backward compatibility)
        with patch(
            "poly.resources.resource.Resource.read_from_file",
            return_value=content_or_file_map,
        ):
            yield


@contextmanager
def mock_variant_attributes_file(file_content, base_path="."):
    """Context manager to mock variant_attributes.yaml file access for tests.

    Mocks read_from_file and os.path.exists/isfile/getmtime for variant_attributes.yaml path.
    Use when tests need to read from variant_attributes.yaml without a real file on disk.

    Args:
        file_content (str): YAML content for the variant_attributes.yaml file.
        base_path (str): Base path for the project (default ".").

    Usage:
        with mock_variant_attributes_file('''variants:
          - name: default
            is_default: true
        '''):
            Variant.discover_resources(".")
    """
    variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")

    def exists_va(path):
        return True if "variant_attributes.yaml" in str(path) else os.path.exists(path)

    def isfile_va(path):
        return True if "variant_attributes.yaml" in str(path) else os.path.isfile(path)

    def getmtime_va(path):
        return 1.0 if "variant_attributes.yaml" in str(path) else os.path.getmtime(path)

    with mock_read_from_file({variant_attributes_path: file_content}):
        with patch(
            "poly.resources.variant_attributes.os.path.exists",
            side_effect=exists_va,
        ), patch(
            "poly.resources.resource.os.path.exists",
            side_effect=exists_va,
        ), patch(
            "poly.resources.resource.os.path.isfile",
            side_effect=isfile_va,
        ), patch(
            "poly.resources.resource.os.path.getmtime",
            side_effect=getmtime_va,
        ):
            yield


CAMPAIGN_TRIGGER_CODE = "def map_contacts(contacts, outbound_campaign):\n    return {}\n"


def campaign_function(name: str, code: str = "", description: str = "") -> dict:
    """Return a campaign node's function as Agent Studio's projection holds it."""
    return {
        "name": name,
        "description": description,
        "code": code,
        "parameters": {"ids": [], "entities": {}},
    }


def campaign_entity(
    campaign_id: str = "CMPGN-ONE",
    name: str = "Reminders",
    nodes: Optional[list[dict]] = None,
    *,
    trigger_label: Optional[str] = "Trigger",
    end_label: Optional[str] = "End",
    trigger_code: str = CAMPAIGN_TRIGGER_CODE,
    function_descriptions: bool = False,
    settings: Optional[dict] = None,
    **fields,
) -> dict:
    """Return an outbound campaign as Agent Studio's projection holds it.

    By default it has a trigger routing to a call, which routes to an end node. `fields` are
    set on the campaign as they are.
    """

    def function(function_name: str, code: str = "") -> dict:
        description = f"{function_name} description" if function_descriptions else ""
        return campaign_function(function_name, code, description)

    if nodes is None:
        nodes = [
            {
                "id": "trigger-1",
                "position": {"x": 0, "y": 0},
                "label": trigger_label,
                "data": {
                    "type": "trigger",
                    "function": function("map_contacts", trigger_code),
                    "routes": [{"targetNodeId": "call-1"}],
                    "sourceType": "csv",
                    "ingestInterval": "daily",
                },
            },
            {
                "id": "call-1",
                "position": {"x": 0, "y": 200},
                "label": "First call",
                "data": {
                    "type": "call",
                    "flowName": "Booking",
                    "function": function("call_args"),
                    "greeting": "Hi",
                    "voicemailEnabled": False,
                    "maxAttempts": 2,
                    "backoff": 1,
                    "backoffUnit": "hours",
                    "routes": [],
                    "defaultRoute": "end-1",
                },
            },
            {
                "id": "end-1",
                "position": {"x": 0, "y": 400},
                "label": end_label,
                "data": {"type": "end", "exitReason": "done", "writebackEnabled": False},
            },
        ]
    return {
        "id": campaign_id,
        "name": name,
        "description": None,
        "status": "draft",
        "settings": {"fromNumber": "+15550100", "country": "US", **(settings or {})},
        "nodes": {"ids": [node["id"] for node in nodes], "entities": {n["id"]: n for n in nodes}},
        "publishedNodes": None,
        "archived": False,
        **fields,
    }


def campaigns_projection(*campaigns: dict) -> dict:
    """Return a projection holding only these outbound campaigns."""
    return {
        "outboundCampaigns": {
            "outboundCampaigns": {
                "ids": [campaign["id"] for campaign in campaigns],
                "entities": {campaign["id"]: campaign for campaign in campaigns},
            }
        }
    }


def campaign_projection(extra_campaigns: tuple[dict, ...] = (), **fields) -> dict:
    """Return a projection holding `campaign_entity(**fields)` and `extra_campaigns`."""
    return campaigns_projection(campaign_entity(**fields), *extra_campaigns)

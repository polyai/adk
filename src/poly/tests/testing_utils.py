"""Util functions for testing

Copyright PolyAI Limited
"""

import os
from contextlib import contextmanager
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

"""API authentication and utility helpers

Copyright PolyAI Limited
"""

import re

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake_keys(value: object) -> object:
    """Recursively convert a JSON value's dict keys from camelCase to snake_case.

    Sourcerer (agent-stream) responds with camelCase keys, unlike the rest of
    the ADK v1 API (served by poly_core), which uses snake_case throughout.
    This normalizes sourcerer responses to the convention the rest of ADK's
    code expects, at the point they're received.
    """
    if isinstance(value, dict):
        return {
            _CAMEL_CASE_BOUNDARY.sub("_", k).lower(): camel_to_snake_keys(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [camel_to_snake_keys(v) for v in value]
    return value


def clean_body(body: dict) -> dict:
    """Clean the body dictionary by removing None values
    as the API schema does not allow them.
    """
    cleaned = {}
    for k, v in body.items():
        if isinstance(v, dict):
            v = clean_body(v)
        if v is not None:
            cleaned[k] = v
    return cleaned


def filter_dict(dict: dict, required_keys: list[str]) -> dict:
    """Clean the dictionary by removing None values."""
    return {k: v for k, v in dict.items() if v is not None and k in required_keys}

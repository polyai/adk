"""API authentication and utility helpers

Copyright PolyAI Limited
"""


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

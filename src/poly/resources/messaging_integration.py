"""Messaging handoff integration transforms.

Converts between the Jupiter API format and the local YAML format.
Handles variant ID/name resolution and per-env credential flattening.

Copyright PolyAI Limited
"""

from typing import Any

import yaml

# Maps API integration type to local CLI name.
INTEGRATION_TYPES: dict[str, dict[str, str]] = {
    "cxone-chat": {
        "api_type": "nice",
        "name": "NICE CXone Messaging",
        "description": "Hand off chat conversations to NICE CXone agents via the Chat SDK.",
    },
}
API_TYPE_TO_LOCAL_NAME: dict[str, str] = {v["api_type"]: k for k, v in INTEGRATION_TYPES.items()}
LOCAL_NAME_TO_API_TYPE: dict[str, str] = {v: k for k, v in API_TYPE_TO_LOCAL_NAME.items()}


def api_response_to_yaml(
    api_response: dict,
    variant_id_to_name: dict[str, str],
) -> str:
    """Convert a Jupiter API response to the local YAML format.

    Args:
        api_response: Raw JSON from the messaging-handoff-integrations endpoint
        variant_id_to_name: Mapping of variant IDs to human-readable names

    Returns:
        YAML string for the local file
    """
    raw_assignments = dict(api_response.get("_assignments", {}))
    default_cred_set = raw_assignments.pop("__default__", "")

    raw_cred_sets = api_response.get("_credential_sets", {})
    credential_sets: dict[str, dict[str, Any]] = {}
    for cred_name, envs in raw_cred_sets.items():
        first_env = next(iter(envs.values()), {})
        credential_sets[cred_name] = {
            k: v.strip() if isinstance(v, str) else v for k, v in first_env.items()
        }

    variants: list[dict[str, Any]] = []
    for variant_id, cred_set in raw_assignments.items():
        entry: dict[str, Any] = {
            "name": variant_id_to_name.get(variant_id, variant_id),
            "credential_set": cred_set,
        }
        if cred_set == default_cred_set:
            entry["is_default"] = True
        variants.append(entry)

    data = {
        "variants": variants,
        "credential_sets": credential_sets,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def yaml_to_api_payload(
    yaml_content: str,
    variant_name_to_id: dict[str, str],
) -> dict:
    """Convert a local YAML file to the Jupiter API payload format.

    Args:
        yaml_content: The raw YAML string from the local file
        variant_name_to_id: Mapping of variant names to IDs

    Returns:
        dict suitable for PUT to the messaging-handoff-integrations endpoint

    Raises:
        ValueError: If the YAML is invalid or missing required fields
    """
    data = yaml.safe_load(yaml_content)
    if not data:
        raise ValueError("YAML file is empty")

    assignments: dict[str, str] = {}
    default_cred_set = ""

    for v in data.get("variants", []):
        name = v.get("name", "")
        variant_id = variant_name_to_id.get(name, name)
        cred_set = v["credential_set"]
        assignments[variant_id] = cred_set
        if v.get("is_default"):
            default_cred_set = cred_set

    if not default_cred_set:
        raise ValueError("No variant has is_default: true")

    assignments["__default__"] = default_cred_set

    envs = ("sandbox", "pre-release", "live")
    credential_sets = data.get("credential_sets", {})
    expanded: dict[str, dict[str, dict[str, Any]]] = {}
    for cred_name, config in credential_sets.items():
        expanded[cred_name] = {env: dict(config) for env in envs}

    for v in data.get("variants", []):
        cred_set = v["credential_set"]
        if cred_set not in credential_sets:
            raise ValueError(
                f"Variant '{v.get('name')}' references unknown credential set '{cred_set}'"
            )

    return {
        "_assignments": assignments,
        "_credential_sets": expanded,
        "_version": 2,
    }

"""JSON file I/O and comparison helpers.

Copyright PolyAI Limited
"""

import json
import os
from typing import Optional


def write_json_file(path: str, data: object) -> None:
    """Write data as pretty-printed JSON with trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def read_json_file(path: str) -> Optional[dict]:
    """Read a JSON file, or None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_dicts(local: dict, remote: dict, prefix: str = "") -> list[dict]:
    """Compare two dicts and return a list of field-level differences.

    Recurses into nested dicts. Each difference is a dict with 'path', 'type',
    and the relevant values.
    """
    local = local or {}
    remote = remote or {}
    changes = []
    all_keys = sorted(set(local) | set(remote))

    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        in_local = key in local
        in_remote = key in remote

        if in_local and not in_remote:
            changes.append({"path": path, "type": "added_locally", "local": local[key]})
        elif in_remote and not in_local:
            changes.append({"path": path, "type": "only_remote", "remote": remote[key]})
        elif local[key] != remote[key]:
            if isinstance(local[key], dict) and isinstance(remote[key], dict):
                changes.extend(diff_dicts(local[key], remote[key], prefix=path))
            else:
                changes.append(
                    {
                        "path": path,
                        "type": "changed",
                        "local": local[key],
                        "remote": remote[key],
                    }
                )

    return changes

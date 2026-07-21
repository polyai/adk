"""JSON file I/O helpers.

Copyright PolyAI Limited
"""

import json
import os
from typing import Optional


def write_json_file(path: str, data: object) -> None:
    """Write data as pretty-printed JSON with trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def read_json_file(path: str) -> Optional[dict]:
    """Read a JSON file, or None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

"""JSON output helpers for machine-readable CLI output.

Copyright PolyAI Limited
"""

import json
import sys

from google.protobuf.json_format import MessageToDict


def json_print(data: dict) -> None:
    """Print data as formatted JSON to stdout.

    Args:
        data: Dictionary to serialize and print.
    """
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def json_progress(data: dict) -> None:
    """Write data as one line of JSON to stderr, flushed, ahead of the result on stdout.

    Args:
        data: Dictionary to serialize and write.
    """
    sys.stderr.write(json.dumps(data, default=str) + "\n")
    sys.stderr.flush()


def commands_to_dicts(commands: list) -> list[dict]:
    """Convert a list of Command protobufs to JSON-serializable dicts.

    Args:
        commands: List of Command protobuf messages.

    Returns:
        list[dict]: Each Command serialized via MessageToDict.
    """
    return [MessageToDict(cmd, preserving_proto_field_name=True) for cmd in commands]

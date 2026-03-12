"""Update the version in pyproject.toml."""

import sys
import tomllib

import tomli_w


def update_version(new_version: str) -> None:
    """Update the version in pyproject.toml."""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    data["project"]["version"] = new_version

    with open("pyproject.toml", "wb") as f:
        tomli_w.dump(data, f)

    print(f"Updated version to {new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: update_version.py <new_version>", file=sys.stderr)
        sys.exit(1)

    new_version = sys.argv[1]
    update_version(new_version)

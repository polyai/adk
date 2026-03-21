"""MkDocs macros hook — exposes project variables for use in docs pages.

Usage in any markdown page:
    Current version: {{ adk_version }}
    Install pin:     pip install polyai-adk=={{ adk_version }}
"""

import os
import tomllib


def define_env(env):  # noqa: ANN001
    """Register macros variables available in all docs pages."""
    toml_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    env.variables["adk_version"] = data["project"]["version"]

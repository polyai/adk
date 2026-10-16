"""Shared pytest fixtures.

Copyright PolyAI Limited
"""

import pytest


@pytest.fixture(autouse=True)
def isolated_path_shadow_check(tmp_path, monkeypatch):
    """Keep the PATH shadow check away from the developer's machine.

    Under pytest ``sys.argv[0]`` is pytest, so whatever ``poly`` is first on the
    host's PATH would look like a shadow: the check would run that binary and write
    to the real ``~/.poly``. Point its files at a throwaway directory and start every
    test from "not shadowed"; tests of the check itself patch what they need.
    """
    from poly.utils import installs

    monkeypatch.setattr(installs, "OTHER_POLY_CACHE_FILE", tmp_path / ".other_poly")
    monkeypatch.setattr(installs, "SHADOW_SEEN_FILE", tmp_path / ".shadow_seen")
    monkeypatch.setattr(installs, "_shadow_field", {})
    yield

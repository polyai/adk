"""Shared pytest fixtures for the ADK test suite.

Copyright PolyAI Limited
"""

import pytest


@pytest.fixture(autouse=True)
def _isolated_library_dir(tmp_path, monkeypatch):
    """Keep the model library cache out of the real ~/.poly while tests run."""
    monkeypatch.setattr("poly.library.LIBRARY_DIR", str(tmp_path / "library"))

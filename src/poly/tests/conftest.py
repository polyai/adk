"""Shared pytest fixtures for the ADK test suite.

Copyright PolyAI Limited
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _isolated_library_dir(tmp_path, monkeypatch):
    """Keep the model library cache out of the real ~/.poly while tests run."""
    monkeypatch.setattr("poly.library.LIBRARY_DIR", str(tmp_path / "library"))


@pytest.fixture(autouse=True)
def _no_live_model_list_calls():
    """Stop library refreshes during pulls and fetches from calling the real API.

    Tests that need model lists patch these again with their own return values.
    """
    with (
        patch("poly.handlers.interface.AgentStudioInterface.get_asr_models", return_value=[]),
        patch("poly.handlers.interface.AgentStudioInterface.get_llm_models", return_value=[]),
    ):
        yield

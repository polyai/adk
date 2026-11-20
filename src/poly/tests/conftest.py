"""Shared pytest fixtures for the ADK test suite.

Copyright PolyAI Limited
"""

import os
import shutil
from unittest.mock import patch

import pytest

# A saved model library for the test project's region, so its files can use model names.
TEST_LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "test_projects", "library")


@pytest.fixture(autouse=True)
def _isolated_library_dir(tmp_path, monkeypatch):
    """Point the model library at a temp copy of the test library, never the real ~/.poly.

    A copy, so a test that refreshes the library can't change the one in the repo.
    """
    library_dir = tmp_path / "library"
    shutil.copytree(TEST_LIBRARY_DIR, library_dir)
    monkeypatch.setattr("poly.library.LIBRARY_DIR", str(library_dir))


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

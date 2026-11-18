"""Shared test setup.

Copyright PolyAI Limited
"""

from unittest.mock import MagicMock

import pytest

from poly.handlers import posthog as posthog_module
from poly.utils import credentials as credentials_module


@pytest.fixture(autouse=True)
def _isolate_home_and_posthog(tmp_path, monkeypatch):
    """Keep every test off the real ~/.poly and off the network.

    Commands now record who signed in and send usage events, so without this a
    test could write a fake identity into the developer's credential file or
    send an event to the real PostHog project. Tests that check these paths
    patch them again themselves.
    """
    monkeypatch.setattr(
        credentials_module, "CREDENTIALS_FILE_PATH", str(tmp_path / "credentials.json")
    )
    monkeypatch.setattr(posthog_module, "TELEMETRY_FILE_PATH", str(tmp_path / "telemetry.json"))
    monkeypatch.setattr(posthog_module, "get_posthog_client", MagicMock())
    # The developer running the suite may have opted out themselves.
    # The suite may itself run under a coding agent, which sets its own markers.
    for name in (
        *posthog_module.TELEMETRY_OPT_OUT_ENV_VARS,
        *posthog_module.AGENT_ENV_MARKERS,
        posthog_module.SIGNUP_REF_ENV_VAR,
    ):
        monkeypatch.delenv(name, raising=False)

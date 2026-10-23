"""Constants for Agent Development Kit

Copyright PolyAI Limited
"""

import os

# User-level state lives here: stored credentials, the update-check stamp, and
# anything else that belongs to the user rather than to a single project.
POLY_HOME_DIR = os.path.expanduser("~/.poly")

# The region names the CLI advertises, keyed to the internal identifier that the
# credential file, the ``POLY_ADK_KEY_<REGION>`` suffixes and the API hosts use.
REGION_NAMES: dict[str, str] = {"us": "us-1", "eu": "euw-1", "uk": "uk-1", "studio": "studio"}
_REGION_DISPLAY_NAMES = {internal: name for name, internal in REGION_NAMES.items()}


def region_display_name(region: str) -> str:
    """The advertised name for an internal region identifier (``uk-1`` -> ``uk``).

    Identifiers without an advertised name (``staging``, ``dev``) are returned as is.
    """
    return _REGION_DISPLAY_NAMES.get(region, region)


DEFAULT_VOICE_IDS: dict[str, str] = {
    "us-1": "VOICE-6fad73f6",  # Anne
    "euw-1": "VOICE-8b814724",  # Ben
    "uk-1": "VOICE-37966683",  # Ben
    "dev": "VOICE-e2b01d55",  # Anne
    "staging": "VOICE-e2b01d55",  # Anne
    "studio": "VOICE-071db756",  # Aria
}

DEFAULT_VOICE_ID_FALLBACK = "VOICE-afe2b8e8"

PERMISSIONS = [
    "home",
    "conversations",
    "pii",
    "call_download",
    "intents",
    "entities",
    "metrics",
    "assistant_analysis",
    "custom_analytics",
    "safety_analytics",
    "about",
    "source_hub",
    "knowledge_base",
    "jupiter_flows",
    "functions",
    "as_api_integrations",
    "rules",
    "variant_management",
    "handoffs",
    "sms",
    "speech_recognition",
    "realtime_config_builder",
    "testing",
    "branch_management",
    "voice",
    "audio_cache",
    "response_control",
    "voice_channel",
    "webchat_channel",
    "environments",
    "settings",
    "numbers",
    "agent_config",
    "integrations",
    "custom_metrics",
    "realtime_config_manager",
    "webchat_configurations",
    "csat",
]

# Data API enums. These mirror the service's request schemas for the metrics
# routes; it rejects anything else with a 400, so the ADK checks them first.
DATA_CHANNELS = ["VOICE-SIP", "CHAT", "WEBCHAT", "SMS", "RCS"]
DATA_CLIENT_ENVS = ["test", "sandbox", "pre-release", "live", "scenarios"]
DATA_INTERVALS = ["hourly", "daily", "weekly", "monthly"]
DATA_AGGS = [
    "sum",
    "avg",
    "min",
    "max",
    "p50",
    "p95",
    "p99",
    "conversation_count",
    "distinct_count",
]
DATA_GROUP_BY = [
    "project_id",
    "channel",
    "deployment_id",
    "variant_id",
    "client_env",
    "experiment_id",
    "experiment_version_id",
    "value_string",
]
DATA_FILTER_OPS = ["eq", "gt", "gte", "lt", "lte", "in", "ex", "exists"]
DATA_LIST_OPS = ("in", "ex")
DATA_HAVING_OPS = ["eq", "gt", "gte", "lt", "lte"]
DATA_MAX_LIMIT = 100
DATA_MAX_OFFSET = 1000
DATA_RATE_LIMIT_PER_MINUTE = 100

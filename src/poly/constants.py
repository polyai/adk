"""Constants for Agent Development Kit

Copyright PolyAI Limited
"""

DEFAULT_VOICE_IDS: dict[str, str] = {
    "us-1": "VOICE-6fad73f6",  # Anne
    "euw-1": "VOICE-8b814724",  # Ben
    "uk-1": "VOICE-37966683",  # Ben
    "dev": "VOICE-e2b01d55",  # Anne
    "staging": "VOICE-e2b01d55",  # Anne
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

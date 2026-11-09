# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = [
    "_Record",
    "ContactJourney",
    "ContactMetadata",
    "LastSend",
    "OutboundCampaign",
    "OutboundCampaignContext",
    "OutboundContact",
    "StepAttempt",
]

from typing import Any


class _Record(dict[str, Any]):
    def copy(self): ...
    def __or__(self, other): ...


ContactMetadata = dict[str, Any]


class StepAttempt(_Record):
    node_id: str
    node_label: str | None
    action_type: str
    channel: str | None
    attempt_number: int
    status: str
    result: str | None
    step_data: dict
    attempted_at: str
    completed_at: str | None


class LastSend(_Record):
    node_id: str
    node_label: str | None
    channel: str
    status: str
    result: str | None
    state: dict
    attempted_at: str | None
    completed_at: str | None


class ContactJourney(_Record):
    enrolled_at: str | None
    current_node_id: str | None
    current_attempt: int
    status: str
    attempts: list[StepAttempt]
    last_send: LastSend | None


class OutboundContact(_Record):
    contact_id: str
    enrolment_id: str | None
    phone: str
    first_name: str | None
    last_name: str | None
    external_id: str | None
    timezone: str
    variant_id: str | None
    consent_verified: bool
    consent_timestamp: str | None
    metadata: ContactMetadata
    journey: ContactJourney


class OutboundCampaign(_Record):
    campaign_id: str
    campaign_name: str
    node_id: str


class OutboundCampaignContext(_Record):
    campaign_id: str
    campaign_name: str
    enrolment_id: str
    node_id: str
    contact_id: str | None
    context: dict | None
    has_context: bool | None
    flow_name: str | None
    amd_flow_name: str | None
    greeting: str | None
    voicemail_script: str | None
    reply_flow_name: str | None


def wrap_campaign_arguments(arguments: dict[str, Any]) -> dict[str, Any]: ...

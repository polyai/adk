# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

__all__ = [
    "ContactJourney",
    "ContactMetadata",
    "OutboundCampaign",
    "OutboundContact",
    "StepAttempt",
]

from typing import TypedDict


class ContactMetadata(TypedDict): ...


class StepAttempt(TypedDict):
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


class ContactJourney(TypedDict):
    enrolled_at: str | None
    current_node_id: str | None
    current_attempt: int
    status: str
    attempts: list[StepAttempt]


class OutboundContact(TypedDict):
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


class OutboundCampaign(TypedDict):
    campaign_id: str
    name: str
    node_id: str

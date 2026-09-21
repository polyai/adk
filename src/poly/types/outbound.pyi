# Copyright PolyAI Limited
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
    attempt_number: int
    channel: str | None
    status: str
    result: str | None
    attempted_at: str
    completed_at: str | None

class ContactJourney(TypedDict):
    enrolled_at: str | None
    current_node_id: str | None
    current_attempt: int
    status: str
    attempts: list[StepAttempt]

class OutboundContact(TypedDict):
    phone: str
    first_name: str | None
    last_name: str | None
    external_id: str | None
    metadata: ContactMetadata
    journey: ContactJourney

class OutboundCampaign(TypedDict):
    campaign_id: str
    name: str
    node_id: str

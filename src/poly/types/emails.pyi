# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from dataclasses import dataclass

@dataclass
class OutgoingEmail:
    to: str
    body: str
    subject: str

    def asdict(self) -> dict: ...

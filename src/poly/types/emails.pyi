# Copyright PolyAI Limited
from dataclasses import dataclass

@dataclass
class OutgoingEmail:
    to: str
    body: str
    subject: str
    def asdict(self) -> dict: ...

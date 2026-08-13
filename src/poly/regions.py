"""Shared Agent Studio region definitions and normalization.

Copyright PolyAI Limited
"""

REGIONS: list[str] = [
    "us-1",
    "euw-1",
    "uk-1",
    "studio",
    "staging",
    "dev",
]

ENTERPRISE_REGIONS: tuple[str, ...] = (
    "us-1",
    "euw-1",
    "uk-1",
)

REGION_ALIASES: dict[str, str] = {
    "us": "us-1",
    "eu": "euw-1",
    "uk": "uk-1",
}


def normalize_region(value: str) -> str:
    """Return the canonical, lowercase identifier for a known region."""
    candidate = value.strip().lower()
    normalized = REGION_ALIASES.get(candidate, candidate)
    if normalized not in REGIONS:
        raise ValueError(f"Unknown region: {value}")
    return normalized

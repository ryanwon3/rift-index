from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceLine:
    champion: str
    text: str
    is_spoken: bool


@dataclass(frozen=True, slots=True)
class IngestSummary:
    indexed: int
    skipped: bool
    rebuilt: bool
    collection_name: str


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


@dataclass(frozen=True, slots=True)
class SearchResult:
    id: str
    champion: str
    text: str
    is_spoken: bool
    similarity: float


@dataclass(frozen=True, slots=True)
class ChampionSummary:
    champion: str
    spoken_count: int
    action_count: int
    total_count: int

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from app.ingest import ingest
from app.models import VoiceLine
from app.search import IndexUnavailableError, SearchService, cosine_similarity
from tests.helpers import KeywordEmbedding


def lines() -> list[VoiceLine]:
    return [
        VoiceLine(champion="Braum", text="Eat, eat and grow strong.", is_spoken=True),
        VoiceLine(champion="Akali", text="Akali eats ramen.", is_spoken=False),
        VoiceLine(champion="Garen", text="For Demacia!", is_spoken=True),
        VoiceLine(champion="Kog'Maw", text="Mmm… food!", is_spoken=True),
    ]


def make_service(path: Path) -> SearchService:
    client = chromadb.PersistentClient(path=str(path))
    embedding = KeywordEmbedding()
    ingest(client, lines(), embedding_function=embedding)
    return SearchService(client, embedding)


@pytest.mark.parametrize(
    ("distance", "expected"),
    [(-0.2, 1.0), (0.0, 1.0), (0.25, 0.75), (1.0, 0.0), (1.4, 0.0)],
)
def test_cosine_similarity_clamps_distance(distance: float, expected: float) -> None:
    assert cosine_similarity(distance) == expected


def test_search_ranks_semantic_matches_and_defaults_to_spoken(tmp_path: Path) -> None:
    service = make_service(tmp_path / "chroma")

    results = service.search("food", limit=10)

    assert [result.champion for result in results[:2]] == ["Braum", "Kog'Maw"]
    assert all(result.is_spoken for result in results)
    assert all(0.0 <= result.similarity <= 1.0 for result in results)


def test_search_combines_champion_and_line_type_filters(tmp_path: Path) -> None:
    service = make_service(tmp_path / "chroma")

    action_results = service.search("food", line_type="action")
    champion_results = service.search("food", champion="Braum", line_type="all")

    assert [(result.champion, result.is_spoken) for result in action_results] == [("Akali", False)]
    assert [result.champion for result in champion_results] == ["Braum"]


def test_champion_summaries_include_spoken_and_action_counts(tmp_path: Path) -> None:
    service = make_service(tmp_path / "chroma")

    summaries = service.champions()

    assert [summary.champion for summary in summaries] == ["Akali", "Braum", "Garen", "Kog'Maw"]
    assert summaries[0].spoken_count == 0
    assert summaries[0].action_count == 1
    assert summaries[1].spoken_count == 1
    assert summaries[1].action_count == 0


def test_persistent_client_can_reopen_and_search_existing_index(tmp_path: Path) -> None:
    path = tmp_path / "chroma"
    make_service(path)

    reopened = SearchService(chromadb.PersistentClient(path=str(path)), KeywordEmbedding())

    assert reopened.is_ready() is True
    assert reopened.search("food", champion="Kog'Maw")[0].text == "Mmm… food!"


def test_search_rejects_an_index_built_with_a_different_embedding_model(tmp_path: Path) -> None:
    service = make_service(tmp_path / "chroma")
    collection = service.client.get_collection(
        "voice_lines_v1",
        embedding_function=service.embedding_function,
    )
    collection.modify(metadata={**collection.metadata, "embedding_model": "different-model"})

    assert service.is_ready() is False
    with pytest.raises(IndexUnavailableError, match="--rebuild"):
        service.search("food")

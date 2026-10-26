from __future__ import annotations

from pathlib import Path

import chromadb
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.search import SearchService
from tests.helpers import KeywordEmbedding
from tests.test_search import make_service


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(make_service(tmp_path / "chroma")))


def test_search_api_returns_documented_shape(client: TestClient) -> None:
    response = client.get("/api/search", params={"q": "food", "limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "food"
    assert payload["champion"] is None
    assert payload["line_type"] == "spoken"
    assert payload["limit"] == 2
    assert payload["count"] == 2
    assert set(payload["results"][0]) == {
        "id",
        "champion",
        "text",
        "is_spoken",
        "similarity",
    }


@pytest.mark.parametrize(
    "params",
    [
        {"q": ""},
        {"q": "  "},
        {"q": "x"},
        {"q": "x" * 201},
        {"q": "food", "line_type": "sound"},
        {"q": "food", "limit": 0},
        {"q": "food", "limit": 51},
    ],
)
def test_search_api_rejects_invalid_queries(client: TestClient, params: dict[str, object]) -> None:
    assert client.get("/api/search", params=params).status_code == 422


def test_search_api_rejects_unknown_champion(client: TestClient) -> None:
    response = client.get("/api/search", params={"q": "food", "champion": "Unknown"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown champion: Unknown"


def test_search_api_returns_empty_results_for_valid_filter_without_matches(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/search",
        params={"q": "food", "champion": "Braum", "line_type": "action"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_champions_api_returns_alphabetized_counts(client: TestClient) -> None:
    response = client.get("/api/champions")

    assert response.status_code == 200
    assert response.json()["champions"][0] == {
        "champion": "Akali",
        "spoken_count": 0,
        "action_count": 1,
        "total_count": 1,
    }


def test_unavailable_index_reports_health_and_search_error(tmp_path: Path) -> None:
    service = SearchService(
        chromadb.PersistentClient(path=str(tmp_path / "empty")),
        KeywordEmbedding(),
    )
    client = TestClient(create_app(service))

    health = client.get("/health")
    search = client.get("/api/search", params={"q": "food"})

    assert health.status_code == 200
    assert health.json()["status"] == "setup_required"
    assert health.json()["index_ready"] is False
    assert health.json()["record_count"] == 0
    assert search.status_code == 503
    assert "python -m app.ingest" in search.json()["detail"]

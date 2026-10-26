from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.test_search import make_service


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(make_service(tmp_path / "chroma")))


def test_explore_page_exposes_accessible_search_contract(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert '<nav class="primary-nav" aria-label="Primary navigation">' in response.text
    assert '<main id="main-content"' in response.text
    assert 'id="search-form"' in response.text
    assert 'name="q"' in response.text
    assert 'id="champion-select"' in response.text
    assert 'name="line_type"' in response.text
    assert 'id="status-region"' in response.text
    assert 'aria-live="polite"' in response.text
    assert 'id="results-grid"' in response.text
    assert 'href="/" aria-current="page"' in response.text


def test_champions_page_exposes_filterable_directory_contract(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/champions")

    assert response.status_code == 200
    assert 'data-page="champions"' in response.text
    assert 'id="champion-filter"' in response.text
    assert 'id="champion-directory"' in response.text
    assert 'href="/champions" aria-current="page"' in response.text


def test_about_page_documents_dataset_scope_and_attribution(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/about")

    assert response.status_code == 200
    assert "32,392" in response.text
    assert "163 champions" in response.text
    assert "historical snapshot" in response.text
    assert "Allan-Cao/lol-voice-lines" in response.text
    assert "not endorsed by Riot Games" in response.text
    assert 'href="/about" aria-current="page"' in response.text


def test_page_does_not_reflect_untrusted_query_markup(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/", params={"q": "<script>alert(1)</script>"})

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text


def test_static_assets_are_served_with_expected_content_types(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    css = client.get("/static/styles.css")
    javascript = client.get("/static/app.js")

    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert javascript.status_code == 200
    assert "javascript" in javascript.headers["content-type"]

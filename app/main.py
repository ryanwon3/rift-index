from __future__ import annotations

from typing import Annotated, Literal

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.config import DATA_DIR, DATASET_COMMIT, EMBEDDING_MODEL
from app.models import ChampionSummary, SearchResult
from app.search import IndexUnavailableError, SearchService

LineType = Literal["spoken", "action", "all"]


class SearchResponse(BaseModel):
    query: str
    champion: str | None
    line_type: LineType
    limit: int
    count: int
    results: list[SearchResult]


class ChampionsResponse(BaseModel):
    champions: list[ChampionSummary]


class HealthResponse(BaseModel):
    status: Literal["ok", "setup_required"]
    index_ready: bool
    record_count: int
    source_revision: str
    embedding_model: str


def default_search_service() -> SearchService:
    client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
    return SearchService(client, DefaultEmbeddingFunction())


def create_app(service: SearchService | None = None) -> FastAPI:
    app = FastAPI(title="Rift Index", version="0.1.0")
    app.state.search_service = service or default_search_service()

    def get_service() -> SearchService:
        return app.state.search_service

    @app.get("/api/search", response_model=SearchResponse)
    def search(
        q: Annotated[str, Query(min_length=2, max_length=200)],
        champion: str | None = None,
        line_type: LineType = "spoken",
        limit: Annotated[int, Query(ge=1, le=50)] = 12,
    ) -> SearchResponse:
        query = q.strip()
        if not 2 <= len(query) <= 200:
            raise HTTPException(status_code=422, detail="Query must contain 2 to 200 characters")

        search_service = get_service()
        try:
            champions = {summary.champion for summary in search_service.champions()}
            if champion is not None and champion not in champions:
                raise HTTPException(status_code=422, detail=f"Unknown champion: {champion}")
            results = search_service.search(
                query,
                champion=champion,
                line_type=line_type,
                limit=limit,
            )
        except IndexUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        return SearchResponse(
            query=query,
            champion=champion,
            line_type=line_type,
            limit=limit,
            count=len(results),
            results=results,
        )

    @app.get("/api/champions", response_model=ChampionsResponse)
    def champions() -> ChampionsResponse:
        try:
            summaries = get_service().champions()
        except IndexUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return ChampionsResponse(champions=summaries)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        search_service = get_service()
        ready = search_service.is_ready()
        metadata = search_service.index_metadata() if ready else {}
        return HealthResponse(
            status="ok" if ready else "setup_required",
            index_ready=ready,
            record_count=int(metadata.get("record_count", 0)),
            source_revision=str(metadata.get("source_revision", DATASET_COMMIT)),
            embedding_model=str(metadata.get("embedding_model", EMBEDDING_MODEL)),
        )

    return app


app = create_app()

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from app.config import COLLECTION_NAME
from app.models import ChampionSummary, SearchResult

LineType = Literal["spoken", "action", "all"]


def cosine_similarity(distance: float) -> float:
    return round(max(0.0, min(1.0, 1.0 - distance)), 4)


class IndexUnavailableError(RuntimeError):
    pass


class SearchService:
    def __init__(self, client: Any, embedding_function: Any) -> None:
        self.client = client
        self.embedding_function = embedding_function

    def _collection_names(self) -> set[str]:
        return {
            collection if isinstance(collection, str) else collection.name
            for collection in self.client.list_collections()
        }

    def _collection(self) -> Any:
        if COLLECTION_NAME not in self._collection_names():
            raise IndexUnavailableError(
                "Voice-line index is not ready. Run `python -m app.ingest` first."
            )
        collection = self.client.get_collection(
            COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )
        if collection.metadata.get("status") != "ready":
            raise IndexUnavailableError(
                "Voice-line index is not ready. Run `python -m app.ingest --rebuild` first."
            )
        return collection

    def is_ready(self) -> bool:
        try:
            collection = self._collection()
        except IndexUnavailableError:
            return False
        expected = collection.metadata.get("record_count")
        return isinstance(expected, int) and collection.count() == expected

    def index_metadata(self) -> dict[str, Any]:
        if not self.is_ready():
            return {}
        collection = self._collection()
        return {**collection.metadata, "record_count": collection.count()}

    def champions(self) -> list[ChampionSummary]:
        collection = self._collection()
        response = collection.get(include=["metadatas"])
        counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for metadata in response.get("metadatas") or []:
            if metadata is None:
                continue
            champion = str(metadata["champion"])
            index = 0 if bool(metadata["is_spoken"]) else 1
            counts[champion][index] += 1
        return [
            ChampionSummary(
                champion=champion,
                spoken_count=values[0],
                action_count=values[1],
                total_count=sum(values),
            )
            for champion, values in sorted(counts.items(), key=lambda item: item[0].casefold())
        ]

    def search(
        self,
        query: str,
        *,
        champion: str | None = None,
        line_type: LineType = "spoken",
        limit: int = 12,
    ) -> list[SearchResult]:
        collection = self._collection()
        conditions: list[dict[str, Any]] = []
        if champion is not None:
            conditions.append({"champion": champion})
        if line_type != "all":
            conditions.append({"is_spoken": line_type == "spoken"})

        where: dict[str, Any] | None
        if len(conditions) == 2:
            where = {"$and": conditions}
        elif conditions:
            where = conditions[0]
        else:
            where = None

        response = collection.query(
            query_texts=[query],
            n_results=min(limit, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = response.get("ids", [[]])[0]
        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]
        results = [
            SearchResult(
                id=identifier,
                champion=str(metadata["champion"]),
                text=document,
                is_spoken=bool(metadata["is_spoken"]),
                similarity=cosine_similarity(distance),
            )
            for identifier, document, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,
                strict=True,
            )
            if document is not None and metadata is not None
        ]
        return sorted(results, key=lambda result: (-result.similarity, result.champion, result.id))

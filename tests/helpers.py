from __future__ import annotations

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class KeywordEmbedding(EmbeddingFunction[Documents]):
    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "rift_index_keyword_test_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        vectors: Embeddings = []
        for document in input:
            text = document.lower()
            vectors.append(
                np.array(
                    [
                        float(any(word in text for word in ("food", "eat", "hungry", "ramen"))),
                        float(any(word in text for word in ("fight", "battle"))),
                        float("demacia" in text),
                        0.25,
                    ],
                    dtype=np.float32,
                )
            )
        return vectors

    def get_config(self) -> dict[str, object]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, object]) -> KeywordEmbedding:
        return KeywordEmbedding()

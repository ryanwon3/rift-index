from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.ingest import ingest
from app.models import VoiceLine
from app.search import SearchService


def test_real_minilm_model_ranks_a_food_line_first(monkeypatch):
    monkeypatch.setattr(
        ONNXMiniLM_L6_V2,
        "DOWNLOAD_PATH",
        Path(".cache/chroma/onnx_models/all-MiniLM-L6-v2"),
    )
    client = chromadb.EphemeralClient()
    embedding_function = DefaultEmbeddingFunction()
    lines = [
        VoiceLine(champion="Braum", text="Eat well and grow strong.", is_spoken=True),
        VoiceLine(champion="Garen", text="Justice will be done.", is_spoken=True),
        VoiceLine(champion="Diana", text="The moon guides my path.", is_spoken=True),
    ]
    ingest(client, lines, embedding_function=embedding_function)

    result = SearchService(client, embedding_function).search(
        "food and being hungry",
        limit=3,
    )

    assert result[0].champion == "Braum"
    assert "Eat" in result[0].text

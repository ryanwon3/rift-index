import importlib
from pathlib import Path

from chromadb.api.types import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2


def test_embedding_model_dir_uses_chroma_default_model_layout() -> None:
    embedding_model_dir = importlib.import_module("app.embeddings").embedding_model_dir

    assert embedding_model_dir(Path("cache")) == Path(
        "cache/chroma/onnx_models/all-MiniLM-L6-v2"
    )


def test_default_embedding_function_configures_requested_model_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    default_embedding_function = importlib.import_module(
        "app.embeddings"
    ).default_embedding_function
    original = ONNXMiniLM_L6_V2.DOWNLOAD_PATH
    monkeypatch.setattr(ONNXMiniLM_L6_V2, "DOWNLOAD_PATH", original)

    embedding_function = default_embedding_function(tmp_path / "model")

    assert isinstance(embedding_function, DefaultEmbeddingFunction)
    assert tmp_path / "model" == ONNXMiniLM_L6_V2.DOWNLOAD_PATH

from pathlib import Path

from chromadb.api.types import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.config import CACHE_DIR, EMBEDDING_MODEL


def embedding_model_dir(cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / "chroma" / "onnx_models" / EMBEDDING_MODEL


def default_embedding_function(
    model_dir: Path | None = None,
) -> DefaultEmbeddingFunction:
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = model_dir or embedding_model_dir()
    return DefaultEmbeddingFunction()

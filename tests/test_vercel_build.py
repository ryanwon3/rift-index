import importlib
from pathlib import Path

import chromadb
import numpy as np
import pytest

from app.config import (
    COLLECTION_NAME,
    DATASET_COMMIT,
    DATASET_SHA256,
    EMBEDDING_MODEL,
)


def vercel_build_module():
    return importlib.import_module("app.vercel_build")


def create_index(data_dir: Path, *, metadata_count: int, actual_count: int) -> None:
    client = chromadb.PersistentClient(path=str(data_dir / "chroma"))
    collection = client.create_collection(
        COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={
            "source_revision": DATASET_COMMIT,
            "source_sha256": DATASET_SHA256,
            "embedding_model": EMBEDDING_MODEL,
            "distance": "cosine",
            "record_count": metadata_count,
            "status": "ready",
        },
    )
    if actual_count:
        collection.add(
            ids=[f"line-{index}" for index in range(actual_count)],
            embeddings=[[1.0, 0.0] for _ in range(actual_count)],
            documents=[f"line {index}" for index in range(actual_count)],
            metadatas=[{"champion": "Annie", "is_spoken": True} for _ in range(actual_count)],
        )


def test_prune_model_archive_removes_only_download_archive(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    extracted = model_dir / "onnx"
    extracted.mkdir(parents=True)
    archive = model_dir / "onnx.tar.gz"
    archive.write_bytes(b"archive")
    model = extracted / "model.onnx"
    model.write_bytes(b"model")

    removed = vercel_build_module().prune_model_archive(model_dir)

    assert removed is True
    assert not archive.exists()
    assert model.read_bytes() == b"model"
    assert vercel_build_module().prune_model_archive(model_dir) is False


def test_validate_built_index_accepts_ready_exact_count(monkeypatch, tmp_path: Path) -> None:
    create_index(tmp_path, metadata_count=1, actual_count=1)
    module = vercel_build_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "EXPECTED_ROWS", 1)

    module.validate_built_index()


def test_validate_built_index_rejects_missing_index(monkeypatch, tmp_path: Path) -> None:
    module = vercel_build_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "EXPECTED_ROWS", 1)

    with pytest.raises(RuntimeError, match="invalid Chroma index"):
        module.validate_built_index()


def test_validate_built_index_rejects_wrong_count(monkeypatch, tmp_path: Path) -> None:
    create_index(tmp_path, metadata_count=2, actual_count=1)
    module = vercel_build_module()
    monkeypatch.setattr(module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(module, "EXPECTED_ROWS", 1)

    with pytest.raises(RuntimeError, match="invalid Chroma index"):
        module.validate_built_index()


def create_model_files(cache_dir: Path) -> Path:
    model_dir = cache_dir / "chroma" / "onnx_models" / EMBEDDING_MODEL / "onnx"
    model_dir.mkdir(parents=True)
    for filename in (
        "config.json",
        "model.onnx",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    ):
        (model_dir / filename).write_bytes(b"present")
    return model_dir


def test_validate_embedding_model_runs_real_shape_smoke_test(monkeypatch, tmp_path: Path) -> None:
    create_model_files(tmp_path)
    calls = []

    class FakeEmbeddingFunction:
        def __call__(self, documents):
            calls.append(documents)
            return [np.full(384, 0.25, dtype=np.float32)]

    module = vercel_build_module()
    monkeypatch.setattr(
        module,
        "default_embedding_function",
        lambda model_dir=None: FakeEmbeddingFunction(),
    )

    module.validate_embedding_model(cache_dir=tmp_path)

    assert calls == [["Rift Index model smoke test"]]


def test_validate_embedding_model_rejects_missing_or_invalid_model(
    monkeypatch, tmp_path: Path
) -> None:
    module = vercel_build_module()
    with pytest.raises(RuntimeError, match="missing required files"):
        module.validate_embedding_model(cache_dir=tmp_path)

    create_model_files(tmp_path)

    class InvalidEmbeddingFunction:
        def __call__(self, documents):
            return [np.array([float("nan")], dtype=np.float32)]

    monkeypatch.setattr(
        module,
        "default_embedding_function",
        lambda model_dir=None: InvalidEmbeddingFunction(),
    )
    with pytest.raises(RuntimeError, match="384 finite values"):
        module.validate_embedding_model(cache_dir=tmp_path)

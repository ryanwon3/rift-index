import importlib
from pathlib import Path

import pytest

from app.config import DATASET_COMMIT


def runtime_chroma_path():
    return importlib.import_module("app.runtime").runtime_chroma_path


def test_local_runtime_uses_data_directory_without_copying(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source = data_dir / "chroma"
    source.mkdir(parents=True)
    (source / "chroma.sqlite3").write_text("local")
    temp_root = tmp_path / "tmp"

    result = runtime_chroma_path()(data_dir, is_vercel=False, temp_root=temp_root)

    assert result == source
    assert not temp_root.exists()


def test_vercel_runtime_copies_once_and_reuses_revision_directory(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source = data_dir / "chroma"
    source.mkdir(parents=True)
    database = source / "chroma.sqlite3"
    database.write_text("bundled")
    temp_root = tmp_path / "tmp"

    first = runtime_chroma_path()(data_dir, is_vercel=True, temp_root=temp_root)
    database.write_text("changed source")
    second = runtime_chroma_path()(data_dir, is_vercel=True, temp_root=temp_root)

    expected = temp_root / f"rift-index-{DATASET_COMMIT[:12]}" / "chroma"
    assert first == expected
    assert second == expected
    assert (expected / "chroma.sqlite3").read_text() == "bundled"


def test_vercel_runtime_rejects_missing_bundled_index(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="bundled Chroma index is missing"):
        runtime_chroma_path()(tmp_path / "missing", is_vercel=True, temp_root=tmp_path / "tmp")


def test_runtime_defaults_to_vercel_environment(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source = data_dir / "chroma"
    source.mkdir(parents=True)
    (source / "chroma.sqlite3").write_text("bundled")
    monkeypatch.setenv("VERCEL", "1")

    result = runtime_chroma_path()(data_dir, temp_root=tmp_path / "tmp")

    assert result != source
    assert (result / "chroma.sqlite3").read_text() == "bundled"

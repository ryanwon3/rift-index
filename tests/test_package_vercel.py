import tarfile
from pathlib import Path

import pytest

from app.package_vercel import create_runtime_archives


def test_create_runtime_archives_packages_index_and_model_only(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "artifacts"
    (data_dir / "chroma").mkdir(parents=True)
    (data_dir / "chroma" / "chroma.sqlite3").write_bytes(b"index")
    model_dir = cache_dir / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx"
    model_dir.mkdir(parents=True)
    (model_dir / "model.onnx").write_bytes(b"model")
    (model_dir.parent / "onnx.tar.gz").write_bytes(b"redundant download archive")
    (cache_dir / "voice_lines.csv").write_text("raw dataset")

    chroma_archive, model_archive = create_runtime_archives(
        data_dir=data_dir,
        cache_dir=cache_dir,
        output_dir=output_dir,
    )

    with tarfile.open(chroma_archive, "r:gz") as archive:
        assert archive.getnames() == ["chroma", "chroma/chroma.sqlite3"]
    with tarfile.open(model_archive, "r:gz") as archive:
        names = archive.getnames()
    assert "chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx" in names
    assert not any(name.endswith("onnx.tar.gz") for name in names)
    assert not any("voice_lines.csv" in name for name in names)


def test_create_runtime_archives_requires_built_index_and_model(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Chroma index"):
        create_runtime_archives(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "artifacts",
        )

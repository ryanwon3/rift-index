from __future__ import annotations

import tarfile
from pathlib import Path

from app.config import CACHE_DIR, DATA_DIR, EMBEDDING_MODEL
from app.vercel_build import validate_built_index, validate_embedding_model

ARTIFACT_DIR = Path(".vercel-artifacts")


def create_runtime_archives(
    *,
    data_dir: Path = DATA_DIR,
    cache_dir: Path = CACHE_DIR,
    output_dir: Path = ARTIFACT_DIR,
) -> tuple[Path, Path]:
    chroma_dir = data_dir / "chroma"
    model_dir = cache_dir / "chroma" / "onnx_models" / EMBEDDING_MODEL
    if not (chroma_dir / "chroma.sqlite3").is_file():
        raise RuntimeError("Chroma index is missing; run `make ingest` first")
    if not (model_dir / "onnx" / "model.onnx").is_file():
        raise RuntimeError("embedding model is missing; run `make ingest` first")

    output_dir.mkdir(parents=True, exist_ok=True)
    chroma_archive = output_dir / "chroma.tar.gz"
    model_archive = output_dir / "model.tar.gz"

    with tarfile.open(chroma_archive, "w:gz") as archive:
        archive.add(chroma_dir, arcname="chroma")
    with tarfile.open(model_archive, "w:gz") as archive:
        archive.add(
            model_dir / "onnx",
            arcname=f"chroma/onnx_models/{EMBEDDING_MODEL}/onnx",
        )

    return chroma_archive, model_archive


def main() -> int:
    validate_built_index()
    validate_embedding_model()
    chroma_archive, model_archive = create_runtime_archives()
    print(f"packaged verified Vercel runtime artifacts: {chroma_archive} and {model_archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

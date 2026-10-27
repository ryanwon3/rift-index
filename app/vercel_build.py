from __future__ import annotations

from pathlib import Path

import chromadb

from app.config import DATA_DIR, EXPECTED_ROWS
from app.embeddings import default_embedding_function, embedding_model_dir
from app.ingest import build_local_index, prepare_dataset
from app.search import SearchService


def prune_model_archive(model_dir: Path) -> bool:
    archive = model_dir / "onnx.tar.gz"
    if not archive.exists():
        return False
    archive.unlink()
    return True


def validate_built_index() -> None:
    client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
    service = SearchService(client, default_embedding_function())
    metadata = service.index_metadata()
    if not service.is_ready() or metadata.get("record_count") != EXPECTED_ROWS:
        raise RuntimeError(
            f"Vercel build produced an invalid Chroma index; expected {EXPECTED_ROWS:,} records"
        )


def main() -> int:
    lines = prepare_dataset()
    summary = build_local_index(lines)
    validate_built_index()
    archive_removed = prune_model_archive(embedding_model_dir())
    action = "reused" if summary.skipped else "built"
    archive_status = "removed model archive" if archive_removed else "model archive absent"
    print(f"{action} verified Vercel index with {len(lines):,} records; {archive_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

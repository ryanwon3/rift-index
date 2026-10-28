from __future__ import annotations

import argparse
import math
from collections.abc import Sequence
from pathlib import Path

import chromadb

from app.config import CACHE_DIR, DATA_DIR, EXPECTED_ROWS
from app.embeddings import default_embedding_function, embedding_model_dir
from app.ingest import build_local_index, prepare_dataset
from app.search import SearchService


def prune_model_archive(model_dir: Path) -> bool:
    archive = model_dir / "onnx.tar.gz"
    if not archive.exists():
        return False
    archive.unlink()
    return True


def validate_built_index(
    *,
    data_dir: Path | None = None,
    expected_rows: int | None = None,
) -> None:
    resolved_data_dir = data_dir or DATA_DIR
    resolved_expected_rows = EXPECTED_ROWS if expected_rows is None else expected_rows
    client = chromadb.PersistentClient(path=str(resolved_data_dir / "chroma"))
    service = SearchService(client, default_embedding_function())
    metadata = service.index_metadata()
    if not service.is_ready() or metadata.get("record_count") != resolved_expected_rows:
        raise RuntimeError(
            "Vercel build produced an invalid Chroma index; "
            f"expected {resolved_expected_rows:,} records"
        )


def validate_embedding_model(*, cache_dir: Path | None = None) -> None:
    resolved_cache_dir = cache_dir or CACHE_DIR
    model_dir = embedding_model_dir(resolved_cache_dir)
    extracted_dir = model_dir / "onnx"
    required_files = (
        "config.json",
        "model.onnx",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    )
    missing = [
        filename
        for filename in required_files
        if not (extracted_dir / filename).is_file()
        or (extracted_dir / filename).stat().st_size == 0
    ]
    if missing:
        raise RuntimeError(
            "Vercel build embedding model is missing required files: " + ", ".join(missing)
        )

    try:
        embeddings = default_embedding_function(model_dir)(["Rift Index model smoke test"])
    except Exception as error:
        raise RuntimeError("Vercel build embedding model smoke test failed") from error

    if len(embeddings) != 1:
        raise RuntimeError("Vercel build embedding model must return one embedding")
    vector = embeddings[0]
    if len(vector) != 384 or not all(math.isfinite(float(value)) for value in vector):
        raise RuntimeError("Vercel build embedding model must return 384 finite values")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the Vercel runtime index.")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify prebuilt runtime files without downloading data or creating embeddings",
    )
    arguments = parser.parse_args(argv)

    if arguments.verify_only:
        validate_built_index()
        validate_embedding_model()
        print(f"verified prebuilt Vercel index with {EXPECTED_ROWS:,} records and model")
        return 0

    lines = prepare_dataset()
    summary = build_local_index(lines)
    validate_built_index()
    archive_removed = prune_model_archive(embedding_model_dir())
    validate_embedding_model()
    action = "reused" if summary.skipped else "built"
    archive_status = "removed model archive" if archive_removed else "model archive absent"
    print(f"{action} verified Vercel index with {len(lines):,} records; {archive_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

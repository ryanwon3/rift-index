from __future__ import annotations

import csv
import hashlib
import io
import os
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from app.config import (
    COLLECTION_NAME,
    DATASET_COMMIT,
    DATASET_SHA256,
    DATASET_URL,
    EMBEDDING_MODEL,
)
from app.models import IngestSummary, VoiceLine


class DatasetIntegrityError(ValueError):
    pass


class IndexMetadataMismatch(RuntimeError):
    pass


def parse_dataset(
    content: bytes,
    *,
    expected_rows: int | None = None,
    expected_champions: int | None = None,
    expected_spoken: int | None = None,
    expected_actions: int | None = None,
) -> list[VoiceLine]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DatasetIntegrityError("dataset is not valid UTF-8") from error

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    required = {"champion", "voice_line", "is_spoken"}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise DatasetIntegrityError(
            "dataset is missing required columns: champion, voice_line, is_spoken"
        )

    lines: list[VoiceLine] = []
    for row_number, row in enumerate(reader, start=2):
        champion = (row.get("champion") or "").strip()
        text = (row.get("voice_line") or "").strip()
        spoken_value = (row.get("is_spoken") or "").strip().upper()
        if not champion or not text:
            raise DatasetIntegrityError(f"row {row_number} has an empty champion or voice line")
        if spoken_value not in {"TRUE", "FALSE"}:
            raise DatasetIntegrityError(f"row {row_number} has invalid is_spoken value")
        lines.append(
            VoiceLine(champion=champion, text=text, is_spoken=spoken_value == "TRUE")
        )

    checks = (
        ("rows", expected_rows, len(lines)),
        ("champions", expected_champions, len({line.champion for line in lines})),
        ("spoken lines", expected_spoken, sum(line.is_spoken for line in lines)),
        ("actions", expected_actions, sum(not line.is_spoken for line in lines)),
    )
    for label, expected, actual in checks:
        if expected is not None and expected != actual:
            raise DatasetIntegrityError(f"expected {expected} {label}, found {actual}")
    return lines


def record_id(line: VoiceLine) -> str:
    identity = f"{line.champion}\0{line.text}\0{int(line.is_spoken)}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def verify_checksum(content: bytes, expected_sha256: str) -> None:
    actual = hashlib.sha256(content).hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise DatasetIntegrityError(
            f"dataset checksum mismatch: expected {expected_sha256}, found {actual}"
        )


def download_dataset(
    destination: Path,
    *,
    url: str = DATASET_URL,
    expected_sha256: str = DATASET_SHA256,
    opener: Callable[[str], bytes] | None = None,
) -> Path:
    if destination.exists():
        try:
            verify_checksum(destination.read_bytes(), expected_sha256)
            return destination
        except DatasetIntegrityError:
            pass

    if opener is None:

        def opener(source_url: str) -> bytes:
            with urllib.request.urlopen(source_url, timeout=30) as response:
                return response.read()

    content = opener(url)
    verify_checksum(content, expected_sha256)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def ingest(
    client: Any,
    lines: Sequence[VoiceLine],
    *,
    embedding_function: Any,
    batch_size: int | None = None,
    source_revision: str = DATASET_COMMIT,
    source_sha256: str = DATASET_SHA256,
    embedding_model: str = EMBEDDING_MODEL,
    rebuild: bool = False,
) -> IngestSummary:
    collection_names = {
        collection if isinstance(collection, str) else collection.name
        for collection in client.list_collections()
    }
    exists = COLLECTION_NAME in collection_names
    expected_metadata = {
        "source_revision": source_revision,
        "source_sha256": source_sha256,
        "embedding_model": embedding_model,
        "distance": "cosine",
        "record_count": len(lines),
        "status": "ready",
    }

    if exists and rebuild:
        client.delete_collection(COLLECTION_NAME)
        exists = False

    if exists:
        collection = client.get_collection(
            COLLECTION_NAME,
            embedding_function=embedding_function,
        )
        if collection.metadata == expected_metadata and collection.count() == len(lines):
            return IngestSummary(
                indexed=0,
                skipped=True,
                rebuilt=False,
                collection_name=COLLECTION_NAME,
            )
        raise IndexMetadataMismatch(
            "existing index metadata does not match this source/model; rerun with --rebuild"
        )

    building_metadata = {**expected_metadata, "status": "building"}
    collection = client.create_collection(
        COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
        metadata=building_metadata,
        embedding_function=embedding_function,
    )
    maximum = client.get_max_batch_size()
    size = min(batch_size or maximum, maximum)
    if size < 1:
        client.delete_collection(COLLECTION_NAME)
        raise ValueError("batch_size must be at least 1")

    try:
        for start in range(0, len(lines), size):
            batch = lines[start : start + size]
            collection.upsert(
                ids=[record_id(line) for line in batch],
                documents=[line.text for line in batch],
                metadatas=[
                    {"champion": line.champion, "is_spoken": line.is_spoken}
                    for line in batch
                ],
            )
        collection.modify(metadata=expected_metadata)
    except Exception:
        client.delete_collection(COLLECTION_NAME)
        raise

    return IngestSummary(
        indexed=len(lines),
        skipped=False,
        rebuilt=rebuild,
        collection_name=COLLECTION_NAME,
    )

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
import numpy as np
import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import COLLECTION_NAME
from app.ingest import (
    DatasetIntegrityError,
    IndexMetadataMismatch,
    download_dataset,
    ingest,
    parse_dataset,
    record_id,
    verify_checksum,
)
from app.models import VoiceLine


class TinyEmbedding(EmbeddingFunction[Documents]):
    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "rift_index_test_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        return [
            np.array(
                [
                    float("food" in document.lower()),
                    float("fight" in document.lower()),
                    1.0,
                ],
                dtype=np.float32,
            )
            for document in input
        ]

    def get_config(self) -> dict[str, object]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, object]) -> TinyEmbedding:
        return TinyEmbedding()


def sample_csv() -> bytes:
    return (
        "\ufeffchampion,voice_line,is_spoken\r\n"
        'Braum,"Eat, eat and grow strong.",TRUE\r\n'
        "Akali,Akali eats ramen.,FALSE\r\n"
        'Kog\'Maw,"Mmm… food!",TRUE\r\n'
    ).encode()


def sample_lines() -> list[VoiceLine]:
    return [
        VoiceLine(champion="Braum", text="Eat, eat and grow strong.", is_spoken=True),
        VoiceLine(champion="Akali", text="Akali eats ramen.", is_spoken=False),
        VoiceLine(champion="Kog'Maw", text="Mmm… food!", is_spoken=True),
    ]


def test_parse_dataset_accepts_utf8_bom_and_preserves_line_types() -> None:
    lines = parse_dataset(
        sample_csv(),
        expected_rows=3,
        expected_champions=3,
        expected_spoken=2,
        expected_actions=1,
    )

    assert lines == sample_lines()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"champion,voice_line\nBraum,Hello\n", "required columns"),
        (b"champion,voice_line,is_spoken\nBraum,Hello,MAYBE\n", "is_spoken"),
    ],
)
def test_parse_dataset_rejects_malformed_rows(payload: bytes, message: str) -> None:
    with pytest.raises(DatasetIntegrityError, match=message):
        parse_dataset(payload)


def test_parse_dataset_rejects_unexpected_source_counts() -> None:
    with pytest.raises(DatasetIntegrityError, match="expected 4 rows, found 3"):
        parse_dataset(sample_csv(), expected_rows=4)


def test_record_id_is_stable_and_includes_every_field() -> None:
    line = VoiceLine(champion="Braum", text="Eat, eat and grow strong.", is_spoken=True)

    assert record_id(line) == "4a0e4349ee0e1bd889f76fe28f45d4b6f5c5d560051cba69bf4ce4916fd1a023"
    assert record_id(line) != record_id(
        VoiceLine(champion="Braum", text="Eat, eat and grow strong.", is_spoken=False)
    )


def test_verify_checksum_rejects_corrupt_content() -> None:
    with pytest.raises(DatasetIntegrityError, match="checksum"):
        verify_checksum(b"corrupt", "0" * 64)


def test_download_dataset_verifies_before_replacing_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "voice_lines.csv"
    destination.write_bytes(b"known-good-cache")

    with pytest.raises(DatasetIntegrityError, match="checksum"):
        download_dataset(
            destination,
            url="https://example.test/voice_lines.csv",
            expected_sha256="0" * 64,
            opener=lambda _: b"corrupt-download",
        )

    assert destination.read_bytes() == b"known-good-cache"
    assert not destination.with_suffix(".csv.tmp").exists()


def test_download_dataset_reuses_a_verified_cache_without_network(tmp_path: Path) -> None:
    destination = tmp_path / "voice_lines.csv"
    payload = sample_csv()
    destination.write_bytes(payload)
    calls = 0

    def opener(_: str) -> bytes:
        nonlocal calls
        calls += 1
        return b"unused"

    result = download_dataset(
        destination,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        opener=opener,
    )

    assert result == destination
    assert calls == 0


def test_ingest_indexes_in_bounded_batches_and_is_idempotent() -> None:
    client = chromadb.EphemeralClient()
    embedding = TinyEmbedding()

    first = ingest(client, sample_lines(), embedding_function=embedding, batch_size=2)
    second = ingest(client, sample_lines(), embedding_function=embedding, batch_size=2)
    collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding)

    assert first.indexed == 3
    assert first.skipped is False
    assert second.indexed == 0
    assert second.skipped is True
    assert collection.count() == 3
    assert collection.metadata["record_count"] == 3
    assert collection.metadata["status"] == "ready"


def test_ingest_requires_rebuild_for_incompatible_source_metadata() -> None:
    client = chromadb.EphemeralClient()
    embedding = TinyEmbedding()
    ingest(client, sample_lines(), embedding_function=embedding)

    with pytest.raises(IndexMetadataMismatch, match="--rebuild"):
        ingest(
            client,
            sample_lines(),
            embedding_function=embedding,
            source_revision="different-source",
        )

    rebuilt = ingest(
        client,
        sample_lines()[:1],
        embedding_function=embedding,
        source_revision="different-source",
        rebuild=True,
    )

    assert rebuilt.rebuilt is True
    assert rebuilt.indexed == 1
    assert client.get_collection(COLLECTION_NAME, embedding_function=embedding).count() == 1

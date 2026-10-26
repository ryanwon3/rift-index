from pathlib import Path

from app import ingest as ingest_module
from app.models import IngestSummary, VoiceLine


def test_prepare_dataset_downloads_and_validates_expected_snapshot(monkeypatch, tmp_path):
    destination = tmp_path / "voice_lines.csv"
    downloaded = b"champion,voice_line,is_spoken\nBraum,Have a snack!,TRUE\n"
    captured: dict[str, object] = {}

    def fake_download(path: Path) -> Path:
        captured["path"] = path
        path.write_bytes(downloaded)
        return path

    def fake_parse(content: bytes, **expected_counts):
        captured["content"] = content
        captured["counts"] = expected_counts
        return [VoiceLine(champion="Braum", text="Have a snack!", is_spoken=True)]

    monkeypatch.setattr(ingest_module, "download_dataset", fake_download)
    monkeypatch.setattr(ingest_module, "parse_dataset", fake_parse)

    lines = ingest_module.prepare_dataset(destination)

    assert lines[0].champion == "Braum"
    assert captured["path"] == destination
    assert captured["content"] == downloaded
    assert captured["counts"] == {
        "expected_rows": 32_392,
        "expected_champions": 163,
        "expected_spoken": 31_240,
        "expected_actions": 1_152,
    }


def test_cli_verify_source_does_not_build_index(monkeypatch, capsys):
    monkeypatch.setattr(
        ingest_module,
        "prepare_dataset",
        lambda: [VoiceLine(champion="Braum", text="Have a snack!", is_spoken=True)],
    )
    called = False

    def fake_build(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(ingest_module, "build_local_index", fake_build)

    assert ingest_module.main(["--verify-source"]) == 0
    assert called is False
    assert "verified 1 rows" in capsys.readouterr().out


def test_cli_rebuilds_local_index_when_requested(monkeypatch, capsys):
    lines = [VoiceLine(champion="Braum", text="Have a snack!", is_spoken=True)]
    monkeypatch.setattr(ingest_module, "prepare_dataset", lambda: lines)
    captured: dict[str, object] = {}

    def fake_build(received, *, rebuild):
        captured["lines"] = received
        captured["rebuild"] = rebuild
        return IngestSummary(
            indexed=1,
            skipped=False,
            rebuilt=True,
            collection_name="voice_lines_v1",
        )

    monkeypatch.setattr(ingest_module, "build_local_index", fake_build)

    assert ingest_module.main(["--rebuild"]) == 0
    assert captured == {"lines": lines, "rebuild": True}
    assert "rebuilt 1 rows" in capsys.readouterr().out

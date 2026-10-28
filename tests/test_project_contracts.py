import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_make_run_prepares_source_and_launches_server():
    result = subprocess.run(
        ["make", "-n", "run"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "uv sync --frozen" in result.stdout
    assert "python -m app.ingest" in result.stdout
    assert "uvicorn app.main:app" in result.stdout


def test_container_and_ci_contracts_are_present():
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert "python:3.11" in dockerfile
    assert "python -m app.ingest" in dockerfile
    assert "/home/rift/.cache/chroma" in dockerfile
    assert "8000:8000" in compose
    assert "/app/.data" in compose
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "--verify-source" in workflow
    assert "docker build" in workflow


def test_public_documentation_contains_required_attribution_and_limits():
    readme = (ROOT / "README.md").read_text()
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    prompt_log = (ROOT / "AI_PROMPT_LOG.md").read_text()

    assert "32,392" in readme
    assert "163 champions" in readme
    assert "First run" in readme
    assert "something to eat before a battle" in readme
    assert "staying brave when you are afraid" in readme
    assert "One CSV row becomes one Chroma item" in readme
    assert "PersistentClient" in readme
    assert "not affiliated with Riot Games" in readme
    assert "Allan-Cao/lol-voice-lines" in readme
    assert "MIT License" in notices
    assert "Riot Games" in notices
    assert "Using python with chroma DB" in prompt_log
    assert "option B is better" in prompt_log
    assert "Before updating, give me the planned readme for me to edit" in prompt_log
    assert "looks good, continue" in prompt_log
    assert "## Assistant" not in prompt_log


def test_vercel_container_build_and_runtime_contracts_are_configured():
    dockerfile = (ROOT / "Dockerfile.vercel").read_text()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "vercel" not in project.get("tool", {})

    assert "FROM python:3.11-slim" in dockerfile
    assert "uv sync --frozen --no-dev --no-install-project" in dockerfile
    assert "COPY .vercel-artifacts/chroma.tar.gz" in dockerfile
    assert "COPY .vercel-artifacts/model.tar.gz" in dockerfile
    assert "python -m app.vercel_build --verify-only" in dockerfile
    assert "python -m app.vercel_build\n" not in dockerfile
    assert "EXPOSE 80" in dockerfile
    assert "uvicorn app.main:app" in dockerfile
    assert "--port ${PORT:-80}" in dockerfile
    command = dockerfile.split("CMD", maxsplit=1)[1]
    assert "python -m app.ingest" not in command

    config = json.loads((ROOT / "vercel.json").read_text())
    assert config["fluid"] is True
    assert "functions" not in config

    makefile = (ROOT / "Makefile").read_text()
    assert "vercel-package:" in makefile
    assert "python -m app.package_vercel" in makefile

    readme = (ROOT / "README.md").read_text()
    assert "vercel deploy --prod --skip-domain" in readme
    assert "vercel promote <tested-production-url>" in readme


def test_generated_vercel_files_are_excluded_from_source_uploads():
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            ".data/chroma.sqlite3",
            ".cache/model.onnx",
            ".vercel/project.json",
            ".vercel-artifacts/chroma.tar.gz",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ignored.stdout.splitlines() == [
        ".data/chroma.sqlite3",
        ".cache/model.onnx",
        ".vercel/project.json",
        ".vercel-artifacts/chroma.tar.gz",
    ]

    docker_ignores = set((ROOT / ".dockerignore").read_text().splitlines())
    assert {".data", ".cache", ".vercel"} <= docker_ignores
    assert ".vercel-artifacts" not in docker_ignores

    vercel_ignores = set((ROOT / ".vercelignore").read_text().splitlines())
    assert {".data", ".cache", ".vercel", "tests", "docs"} <= vercel_ignores
    assert ".vercel-artifacts" not in vercel_ignores

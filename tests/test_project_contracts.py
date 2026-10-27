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
    assert "not affiliated with Riot Games" in readme
    assert "Allan-Cao/lol-voice-lines" in readme
    assert "MIT License" in notices
    assert "Riot Games" in notices
    assert "Using python with chroma DB" in prompt_log
    assert "option B is better" in prompt_log
    assert "## Assistant" not in prompt_log


def test_vercel_build_and_bundle_contracts_are_configured():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    vercel = project["tool"]["vercel"]
    assert vercel["entrypoint"] == "app.main:app"
    assert vercel["scripts"]["build"] == "python -m app.vercel_build"

    config = json.loads((ROOT / "vercel.json").read_text())
    function = config["functions"]["app/main.py"]
    assert config["fluid"] is True
    assert function["maxDuration"] == 60
    assert ".data/**" in function["includeFiles"]
    assert ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/**" in function[
        "includeFiles"
    ]
    assert isinstance(function["excludeFiles"], str)
    assert "tests/**" in function["excludeFiles"]


def test_generated_vercel_files_are_excluded_from_source_uploads():
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            ".data/chroma.sqlite3",
            ".cache/model.onnx",
            ".vercel/project.json",
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
    ]

    docker_ignores = set((ROOT / ".dockerignore").read_text().splitlines())
    assert {".data", ".cache", ".vercel"} <= docker_ignores

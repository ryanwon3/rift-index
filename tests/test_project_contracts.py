import subprocess
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

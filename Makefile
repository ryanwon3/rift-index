UV ?= uv

.PHONY: setup ingest rebuild verify-source vercel-package run test lint format

setup:
	$(UV) sync --frozen --extra dev

ingest: setup
	$(UV) run --no-sync python -m app.ingest

rebuild: setup
	$(UV) run --no-sync python -m app.ingest --rebuild

verify-source: setup
	$(UV) run --no-sync python -m app.ingest --verify-source

vercel-package: ingest
	$(UV) run --no-sync python -m app.package_vercel

run: setup
	$(UV) run --no-sync python -m app.ingest
	$(UV) run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test: setup
	$(UV) run --no-sync pytest

lint: setup
	$(UV) run --no-sync ruff check .
	$(UV) run --no-sync ruff format --check .

format: setup
	$(UV) run --no-sync ruff check --fix .
	$(UV) run --no-sync ruff format .

# Rift Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a local-first semantic League of Legends voice-line search website.

**Architecture:** FastAPI serves Jinja pages and JSON endpoints. A focused ingestion layer downloads and verifies a pinned CSV, while a search service owns a persistent Chroma collection using local MiniLM embeddings.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, vanilla JavaScript, ChromaDB, pytest, Ruff, Docker.

**Spec:** `docs/superpowers/specs/2026-10-25-rift-index-design.md`

## Global Constraints

- Keep all generated data under `.data/` or `.cache/` and out of Git.
- Require no paid API keys and make first-run network needs explicit.
- Preserve exact dataset revision, checksum, counts, attribution, and disclaimer from the spec.
- Use deterministic IDs and idempotent ingestion; never silently mix source/model revisions.
- Default search to spoken lines and label similarity as ranking, not confidence.

## Review Focus

- Interrupted or corrupt dataset downloads must not replace a valid cached source.
- Re-running ingestion must not duplicate records.
- Unknown champions and unavailable indexes must return actionable API errors.
- Quote text must render as text, never executable markup.
- Narrow layouts must retain every search/filter action without horizontal clipping.

---

### Task 1: Dataset ingestion and persistent index

**Files:** `app/config.py`, `app/models.py`, `app/ingest.py`, `tests/test_ingest.py`, dependency metadata.

**Interfaces:** Produce `VoiceLine`, `parse_dataset`, `record_id`, `download_dataset`, `ingest`, and the collection/source constants consumed by later tasks.

- [ ] Write and run failing tests for BOM parsing, schema validation, checksum failure, deterministic IDs, count validation, batching, idempotency, and rebuild requirements.
- [ ] Implement the minimal ingestion layer and configuration to pass.
- [ ] Run the ingestion test module and the full suite.
- [ ] Commit the independently working ingestion slice.

### Task 2: Search service and API contracts

**Files:** `app/search.py`, `app/main.py`, `tests/test_search.py`, `tests/test_api.py`.

**Interfaces:** Produce `SearchService.search`, `SearchResult`, `/api/search`, `/api/champions`, and `/health` with the spec's exact validation and response fields.

- [ ] Write and run failing tests for cosine conversion, filtering, persistence, validation, unknown champions, and unavailable index behavior.
- [ ] Implement the search service and API routes to pass.
- [ ] Run API/search modules and the full suite.
- [ ] Commit the independently working backend slice.

### Task 3: Champion Codex web experience

**Files:** `app/templates/`, `app/static/`, `tests/test_pages.py`.

**Interfaces:** Produce Explore, Champions, and About pages that consume only the public JSON endpoints and preserve URL-synchronized search state.

- [ ] Write and run failing page-contract tests for navigation, forms, safe data binding, states, and accessibility landmarks.
- [ ] Implement the responsive Jinja/CSS/JavaScript experience matching the approved Option B mockup.
- [ ] Run page tests and the full suite; perform browser QA at desktop and narrow widths.
- [ ] Commit the independently working frontend slice.

### Task 4: Local/Docker workflows and documentation

**Files:** `Makefile`, `Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`, `README.md`, `AI_PROMPT_LOG.md`, `LICENSE`, attribution files.

**Interfaces:** Produce `make run`, `docker compose up --build`, CI test/lint/source-verification/Docker jobs, and complete public documentation.

- [ ] Add behavior tests for executable helper commands where practical, then add the workflow/configuration files.
- [ ] Add the README, prompt-only log, license, and third-party notices.
- [ ] Run local command checks, the full suite, and Ruff.
- [ ] Commit the operational/documentation slice.

### Task 5: Real-data verification, final review, and publication

**Files:** all repository files as required by verified findings.

**Interfaces:** Produce a clean reviewed branch, public GitHub repository, and green CI run.

- [ ] Verify the pinned full dataset, real local embedding behavior for a food query, and application startup.
- [ ] Run full tests, lint, browser QA, source integrity checks, and the Docker build where available.
- [ ] Conduct fresh whole-branch review; fix Critical/Important findings with RED→GREEN tests.
- [ ] Merge to `main`, re-authenticate `gh` as `ryanwon3`, create `ryanwon3/rift-index`, push, and verify GitHub Actions.


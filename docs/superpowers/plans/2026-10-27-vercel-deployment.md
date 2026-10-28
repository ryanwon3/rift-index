# Vercel Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Rift Index as a verified public Vercel FastAPI application while retaining bundled MiniLM embeddings and Chroma semantic search.

**Architecture:** A local packaging step validates the existing index and performs a real MiniLM inference smoke test, then creates ignored Chroma/model archives without the raw CSV. Vercel's Container Runtime extracts and revalidates those archives while building a Python 3.11 image. At runtime, FastAPI copies the immutable Chroma files into a revision-specific directory under writable `/tmp`, then opens that copy with `PersistentClient`; local and Docker workflows continue using `.data` directly.

**Tech Stack:** Python 3.11 on Vercel Container Runtime, FastAPI, Chroma 1.5.9, ONNX MiniLM, pytest, Ruff, Vercel CLI

**Spec:** `docs/superpowers/specs/2026-10-27-vercel-deployment-design.md`

## Global Constraints

- Preserve the existing public pages and API contracts.
- Keep dataset revision `85f70fb891f2471eda8a7a773479106b0d3bf88f`, SHA-256 `a183f3a540bdee0299bdf58b732520a8f0acfc3baee10654c658048708a230b8`, and expected count `32,392`.
- Keep `all-MiniLM-L6-v2`, cosine distance, and Chroma as the search implementation.
- Do not commit generated data, model weights, Chroma files, Vercel outputs, or local project-link metadata.
- Do not require a paid inference API or durable runtime filesystem writes.
- Verify a preview deployment before promoting the same tested artifact to production.

## Review Focus

- Missing bundled Chroma source must fail initialization clearly instead of creating an empty production index; Task 2 tests this.
- A warm container instance must reuse its `/tmp` copy rather than copy 90 MB on every request; Task 2 tests this.
- Local and Docker execution must continue opening `.data/chroma` directly; Task 2 tests this.
- A complete extracted model must remain usable while the redundant download archive is excluded; Task 5 tests this with a real inference smoke test.
- Build output with a wrong record count or incompatible metadata must fail before deployment; Task 3 tests this.

---

### Task 1: Deployment-aware embedding cache

**Files:**
- Create: `app/embeddings.py`
- Modify: `app/ingest.py`
- Modify: `app/main.py`
- Modify: `compose.yaml`
- Test: `tests/test_embeddings.py`

**Interfaces:**
- Consumes: `app.config.CACHE_DIR`, `app.config.EMBEDDING_MODEL`.
- Produces: `embedding_model_dir(cache_dir: Path = CACHE_DIR) -> Path` and `default_embedding_function(model_dir: Path | None = None) -> DefaultEmbeddingFunction`.

- [ ] **Step 1: Write failing embedding-path tests**

Add tests asserting that `embedding_model_dir(Path("cache"))` returns `cache/chroma/onnx_models/all-MiniLM-L6-v2`, and that `default_embedding_function(model_dir)` configures `ONNXMiniLM_L6_V2.DOWNLOAD_PATH` before returning a Chroma default embedding function.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/pytest tests/test_embeddings.py -v`
Expected: FAIL because `app.embeddings` does not exist.

- [ ] **Step 3: Implement the embedding factory and adopt it**

Create the two typed functions in `app/embeddings.py`; replace direct `DefaultEmbeddingFunction()` calls in ingestion and app startup with the factory. Remove the now-redundant dedicated home-directory Chroma model volume from `compose.yaml`.

- [ ] **Step 4: Run focused and ingestion tests**

Run: `.venv/bin/pytest tests/test_embeddings.py tests/test_ingest.py tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/embeddings.py app/ingest.py app/main.py compose.yaml tests/test_embeddings.py
git commit -m "feat: configure bundled embedding cache"
```

### Task 2: Read-only bundle to writable runtime index

**Files:**
- Create: `app/runtime.py`
- Modify: `app/main.py`
- Test: `tests/test_runtime.py`

**Interfaces:**
- Consumes: `app.config.DATASET_COMMIT`, `app.config.DATA_DIR`.
- Produces: `runtime_chroma_path(data_dir: Path = DATA_DIR, *, is_vercel: bool | None = None, temp_root: Path | None = None) -> Path`.

- [ ] **Step 1: Write failing runtime-path tests**

Add tests that assert local mode returns `<data_dir>/chroma` without copying, Vercel mode copies all source files into `<temp_root>/rift-index-85f70fb891f2/chroma`, a second call reuses that directory, and a missing source raises `RuntimeError` naming the missing bundled index.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/pytest tests/test_runtime.py -v`
Expected: FAIL because `app.runtime` does not exist.

- [ ] **Step 3: Implement atomic per-instance preparation**

Implement `runtime_chroma_path` using `VERCEL == "1"` as the default mode, a revision-specific `/tmp` target, a process-specific staging directory, `shutil.copytree`, and atomic rename. Update `default_search_service()` to open the returned path.

- [ ] **Step 4: Run runtime and API tests**

Run: `.venv/bin/pytest tests/test_runtime.py tests/test_api.py tests/test_search.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/runtime.py app/main.py tests/test_runtime.py
git commit -m "feat: prepare chroma index for vercel runtime"
```

### Task 3: Reproducible Vercel build and project contract

**Files:**
- Create: `app/vercel_build.py`
- Create: `vercel.json`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `.dockerignore`
- Modify: `README.md`
- Modify: `AI_PROMPT_LOG.md`
- Test: `tests/test_vercel_build.py`
- Test: `tests/test_project_contracts.py`

**Interfaces:**
- Consumes: `prepare_dataset()`, `build_local_index()`, `SearchService`, `embedding_model_dir()`, `EXPECTED_ROWS`.
- Produces: `prune_model_archive(model_dir: Path) -> bool`, `validate_built_index() -> None`, and `main() -> int` in `app.vercel_build`.

- [ ] **Step 1: Write failing build-helper and contract tests**

Add tests asserting archive pruning removes only `onnx.tar.gz`, validation accepts exactly 32,392 compatible records and rejects missing/wrong indexes, `pyproject.toml` declares `app.main:app` plus `python -m app.vercel_build`, `vercel.json` includes `.data/**` and extracted model files while excluding tests, and ignore files keep generated outputs out of Git and Docker source.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/pytest tests/test_vercel_build.py tests/test_project_contracts.py -v`
Expected: FAIL because the build module and Vercel configuration do not exist.

- [ ] **Step 3: Implement the Vercel build contract**

Implement the build helper by running the existing checksum/count-verified ingestion, validating readiness and exact count, deleting the redundant model archive, and printing a concise summary. Configure the FastAPI entrypoint/build command, include generated assets, exclude development-only files, set a 60-second function duration, and enable Fluid compute.

- [ ] **Step 4: Document deployment behavior and append verbatim prompts**

Add a Vercel section to `README.md` describing the 10–20 minute first build, read-only bundle plus `/tmp` copy, Large Functions, local/generated-file behavior, and CLI deployment. Append the dated user deployment prompts and selections to `AI_PROMPT_LOG.md` without AI responses or hidden context.

- [ ] **Step 5: Run the full local verification suite**

Run: `.venv/bin/ruff check .`
Expected: `All checks passed!`

Run: `.venv/bin/pytest`
Expected: all tests pass.

Run: `.venv/bin/python -m app.ingest --verify-source`
Expected: `verified 32,392 rows from source revision 85f70fb891f2471eda8a7a773479106b0d3bf88f`.

- [ ] **Step 6: Commit**

```bash
git add .dockerignore .gitignore AI_PROMPT_LOG.md README.md app/vercel_build.py pyproject.toml vercel.json tests/test_project_contracts.py tests/test_vercel_build.py docs/superpowers/specs/2026-10-27-vercel-deployment-design.md docs/superpowers/plans/2026-10-27-vercel-deployment.md
git commit -m "feat: add reproducible vercel deployment"
```

### Task 4: Preview verification and production release

**Files:**
- Generated and ignored: `.vercel/project.json`
- Remote mutation: Vercel project and deployments
- Remote mutation: GitHub `main`

**Interfaces:**
- Consumes: the verified repository at the Task 3 commit and Vercel CLI authentication.
- Produces: a READY production deployment, public Vercel URL, and pushed GitHub commit.

- [ ] **Step 1: Push the verified implementation**

Run: `git push origin main`
Expected: GitHub accepts the new commits and local `main` matches `origin/main`.

- [ ] **Step 2: Authenticate and resolve the Vercel target**

Run the pinned/current Vercel CLI login flow, deliberately wait for the user to authorize it, link a new project named `rift-index`, then run `vercel project inspect --non-interactive` and confirm the reported owner and project before deployment.

- [ ] **Step 3: Deploy a preview and wait for READY**

Run: `vercel deploy --target preview`
Expected: a preview URL whose deployment inspection status becomes `READY`; the remote build logs show 32,392 indexed or an already-current compatible index.

- [ ] **Step 4: Exercise the preview end to end**

Use `vercel curl` against the preview and assert: `/` returns HTML with `Rift Index`, `/health` returns `status=ok`, `index_ready=true`, and `record_count=32392`; `/api/champions` contains 163 champions; `/api/search?q=food&line_type=spoken&limit=5` returns five ranked results with similarity values.

- [ ] **Step 5: Stage and promote the tested production artifact**

Create a production deployment without assigning the production domain, repeat the health and semantic-search checks against it, then promote that exact deployment. Confirm the resulting production alias returns the same healthy responses.

- [ ] **Step 6: Inspect errors and repository state**

Check Vercel runtime logs for errors since deployment, confirm the GitHub Actions workflow is green, and run `git status --short` plus `git rev-parse HEAD`/`git rev-parse origin/main` to prove the checkout is clean and synchronized.

### Task 5: Container-runtime pivot

**Files:**
- Create: `Dockerfile.vercel`
- Modify: `vercel.json`
- Modify: `README.md`
- Modify: `tests/test_project_contracts.py`

**Interfaces:**
- Consumes: `python -m app.vercel_build`, `app.main:app`, Vercel Container Runtime port resolution.
- Produces: a build-time-verified OCI image that serves the existing FastAPI application on `${PORT:-80}` without runtime ingestion.

- [x] **Step 1: Write failing container-contract tests**

Add tests asserting `Dockerfile.vercel` uses Python 3.11, installs the locked production dependencies, validates the prebuilt Chroma/model artifacts during image construction, starts Uvicorn on `${PORT:-80}`, and never runs ingestion from `CMD`. Assert `vercel.json` no longer configures the native `app/main.py` function. Test the artifact packager independently and prove that it excludes the raw CSV.

- [x] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/pytest tests/test_project_contracts.py -v`
Expected: FAIL because `Dockerfile.vercel` does not exist and native Python Function configuration remains.

- [x] **Step 3: Implement the container contract**

Create `Dockerfile.vercel` from the existing locked Python image workflow, unpack and verify the locally generated model and Chroma artifacts as the non-root user, expose port 80, and start the existing FastAPI app without ingestion. Add `app.package_vercel` and `make vercel-package` so the ignored artifacts are generated only after the local index passes metadata/count validation. Reduce `vercel.json` to container-compatible project configuration and update the README deployment explanation.

- [x] **Step 4: Run focused and full local verification**

Run: `.venv/bin/pytest tests/test_project_contracts.py -v`
Expected: PASS.

Run: `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest`
Expected: all checks pass.

- [x] **Step 5: Deploy and verify before production**

Set the linked Vercel project's framework to Container. The clean remote-ingestion preview must be allowed to reach a definitive result; if it exceeds Vercel's 45-minute build limit, package the locally verified artifacts instead of performing inference during the remote build. Deploy a protected preview and verify `/`, `/health`, `/api/champions`, and `/api/search`. Stage a production deployment with `--skip-domain`, repeat the checks, then promote that exact deployment.

- [ ] **Step 6: Commit and synchronize**

Commit the container contract and approved README update, push `main`, confirm GitHub Actions succeeds, scan production runtime logs, and verify local `HEAD` matches `origin/main`.

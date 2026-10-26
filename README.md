# Rift Index

Rift Index is a local-first semantic search engine for League of Legends
voice-line transcripts. Ask for an idea—such as “food and being hungry”—and it
ranks lines by meaning instead of requiring exact keyword matches.

The site uses FastAPI and server-rendered Jinja pages, vanilla JavaScript,
persistent Chroma storage, and the local `all-MiniLM-L6-v2` embedding model. It
does not require an API key, user account, or hosted database.

## What is included

- Natural-language semantic search with champion and line-type filters
- Ranked transcript cards with cosine similarity shown as a ranking signal,
  not confidence
- A searchable champion directory and transparent dataset notes
- Persistent, idempotent Chroma ingestion with deterministic record IDs
- Checksum-verified, immutable source data
- Python and Docker workflows plus automated tests and CI

## Dataset

The source is [Allan-Cao/lol-voice-lines](https://github.com/Allan-Cao/lol-voice-lines),
pinned to commit `85f70fb891f2471eda8a7a773479106b0d3bf88f` and SHA-256
`a183f3a540bdee0299bdf58b732520a8f0acfc3baee10654c658048708a230b8`.
The verified snapshot contains:

| Coverage | Count |
| --- | ---: |
| Total rows | 32,392 |
| Champions | 163 champions |
| Spoken lines | 31,240 |
| Non-spoken actions | 1,152 |

This is an intentionally historical English-language snapshot. It can contain
upstream transcription or cleaning artifacts and does not include champions or
line changes added after the snapshot. Rift Index indexes text only; it neither
ships nor plays game audio.

## Run with Python

Requirements:

- Python 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- `make` (optional; the equivalent commands are shown below)

Start the application:

```bash
git clone https://github.com/ryanwon3/rift-index.git
cd rift-index
make run
```

Then open <http://127.0.0.1:8000>.

Without Make:

```bash
uv sync --frozen --extra dev
uv run --no-sync python -m app.ingest
uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### First run

The first run needs internet access twice: once for the pinned CSV and once for
the local embedding model. It can take several minutes while 32,392 vectors are
created. The verified CSV is stored in `.cache/` and the persistent Chroma index
in `.data/`; both are ignored by Git. Later launches reuse those files and do
not re-index a compatible collection.

To discard and recreate the index:

```bash
make rebuild
```

Ingestion refuses to mix an existing index with a different source revision,
checksum, embedding model, distance metric, or row count. When that happens,
it prints an explicit instruction to use `--rebuild`.

## Run with Docker

```bash
docker compose up --build
```

Open <http://127.0.0.1:8000>. Named volumes preserve the downloaded source,
model cache, and Chroma index between container restarts. The first container
start still requires network access and performs the same verified ingestion.

## Commands

```bash
make run             # prepare data/index and launch the development server
make ingest          # idempotently prepare the index
make rebuild         # replace the local index
make verify-source   # checksum and count verification; no model download
make test            # run pytest
make lint            # run Ruff checks and formatting verification
make format          # apply Ruff fixes and formatting
```

The ingestion command is also available directly:

```bash
python -m app.ingest [--rebuild] [--verify-source]
```

Set `RIFT_INDEX_DATA_DIR` or `RIFT_INDEX_CACHE_DIR` to move generated files out
of their default `.data/` and `.cache/` directories.

## API

### `GET /api/search`

Parameters:

- `q` — required, 2–200 characters
- `champion` — optional exact champion name
- `line_type` — `spoken` (default), `action`, or `all`
- `limit` — 1–50, default 12

Example:

```bash
curl 'http://127.0.0.1:8000/api/search?q=food%20and%20being%20hungry&line_type=spoken&limit=5'
```

The response includes the normalized query metadata and results shaped as
`{id, champion, text, is_spoken, similarity}`. `similarity` is clamped cosine
similarity used for relative ranking. It is not a probability or confidence
score.

### `GET /api/champions`

Returns alphabetized champions with spoken, action, and total counts.

### `GET /health`

Returns service status, index readiness, indexed record count, source revision,
and embedding model. Search endpoints return HTTP 503 with setup instructions
until the index is ready.

Interactive OpenAPI documentation is available at <http://127.0.0.1:8000/docs>.

## Architecture

```text
browser -> FastAPI/Jinja + JSON API -> SearchService -> persistent Chroma
                                                        ^
pinned CSV -> checksum/count validation -> local MiniLM embeddings
```

`app.ingest` owns source verification and collection construction.
`SearchService` is the only query layer and applies Chroma metadata filters.
The web UI talks only to the public JSON routes, so URL state and API behavior
remain testable independently of the templates.

## Troubleshooting

**The app says the index is not ready.** Run `make ingest`. If it reports
incompatible metadata, run `make rebuild`.

**A model or CSV download fails.** Confirm network access and retry. A failed or
checksum-invalid download never replaces a valid cached CSV.

**Port 8000 is already in use.** Start Uvicorn on another port, for example
`uv run uvicorn app.main:app --port 8080`, or change the Compose port mapping.

**The first search is slow.** Initial model loading and the first embedding can
take longer than later searches. Ingestion itself is cached after completion.

**Docker cannot write its volumes.** Remove only the named Rift Index volumes or
run the Python workflow. Do not copy a partially built `.data/chroma` directory
between platforms.

## Testing

```bash
make lint
make test
make verify-source
```

CI runs linting, unit/integration tests, pinned-source verification, and a Docker
image build. Generated datasets, model files, and indexes are never committed.

## Attribution and license

Application code is MIT licensed; see [LICENSE](LICENSE). The upstream dataset
is also MIT licensed by Allan Cao, and its exact notice is retained in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The upstream project states
that the transcripts were cleaned from League of Legends Wiki data.

League of Legends, its champions, trademarks, and voice-line text belong to
Riot Games and their respective rights holders. Rift Index is not affiliated with Riot Games
and is not endorsed by Riot Games.

The development prompt record is in [AI_PROMPT_LOG.md](AI_PROMPT_LOG.md).

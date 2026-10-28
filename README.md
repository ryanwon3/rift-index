# Rift Index

Rift Index is a local-first semantic search engine for League of Legends
voice-line transcripts. Ask for an idea—such as “food and being hungry”—and it
ranks lines by meaning instead of requiring exact keyword matches.

I chose voice lines because they are short, expressive pieces of natural
language that make the difference between literal keyword matching and
meaning-based retrieval easy to see.

The site uses FastAPI and server-rendered Jinja pages, vanilla JavaScript,
persistent Chroma storage, and the local `all-MiniLM-L6-v2` embedding model. It
does not require an API key, user account, or hosted database.

## Live application

- Vercel: <https://rift-index.vercel.app>
- GitHub: <https://github.com/ryanwon3/rift-index>

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

One CSV row becomes one Chroma item. Each row is already a short champion
voice line or action, so Rift Index does not split it into smaller chunks. The
searchable document is the transcript text, and each item has two metadata
fields:

- `champion` — the champion associated with the line
- `is_spoken` — whether the item is spoken dialogue or a non-spoken action

Each item receives a deterministic SHA-256 ID derived from its champion, text,
line type, and duplicate occurrence number. The Chroma collection also records
the source revision and checksum, embedding model, distance metric, record
count, and readiness status so incompatible indexes cannot be mixed.

This is an intentionally historical English-language snapshot. It can contain
upstream transcription or cleaning artifacts and does not include champions or
line changes added after the snapshot. Rift Index indexes text only; it neither
ships nor plays game audio.

## Run with Python

Requirements:

- Python 3.11
- Git
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

## Adding and searching items

Version one does not allow visitors to submit arbitrary voice lines through
the website. A maintainer adds items by updating the source CSV or pinned
dataset revision and rebuilding the index:

```bash
uv run --no-sync python -m app.ingest --rebuild
```

Users search from the Explore page with a natural-language description and can
optionally filter by champion or by `spoken`, `action`, or `all` line types.
The same operation is available through `GET /api/search`.

## Semantic-search examples

These examples were run against the complete pinned index with the default
spoken-line filter. They show why semantic search is useful beyond literal
keyword matching.

### Query 1: `something to eat before a battle`

Top result:

> **Zac:** “I could really use a snack right now.”

A literal search for the important query words—`eat` and `battle`—would miss
this result because neither appears in the line. The embedding model connects
the idea of eating with needing a snack.

### Query 2: `staying brave when you are afraid`

Top result:

> **Master Yi:** “Fear will not save you.”

An exact keyword search for `brave` or `afraid` would miss this line. Vector
search recognizes `fear` as expressing the same idea as being afraid and ranks
the line by that meaning.

## Obtaining and loading the data

The raw CSV, model files, and generated vector index are intentionally not
committed. Running ingestion downloads the CSV directly from the pinned GitHub
revision, verifies its SHA-256 checksum and expected counts, embeds every row,
and stores the result in persistent Chroma storage:

```bash
uv sync --frozen --extra dev
uv run --no-sync python -m app.ingest
```

The downloaded CSV and embedding-model cache live under `.cache/`; the Chroma
index lives under `.data/chroma/`. Both directories are ignored by Git. Use
`--rebuild` to replace an existing compatible index after changing its source.

## Vector database and embedding model

Rift Index uses Chroma's `PersistentClient`, cosine distance, and the local
`all-MiniLM-L6-v2` model through Chroma's ONNX embedding function. It uses no
paid inference API.

The first ingestion downloads the pinned CSV and embedding model and then
creates 32,392 vectors, so it requires internet access and can take several
minutes. Later runs reuse the verified CSV, extracted model, and persistent
index.

## Run with Docker

```bash
docker compose up --build
```

Open <http://127.0.0.1:8000>. Named volumes preserve the downloaded source,
model cache, and Chroma index between container restarts. The first container
start still requires network access and performs the same verified ingestion.

## Deploy to Vercel

Rift Index deploys the existing FastAPI application with Vercel's Container
Runtime. Because generating 32,392 embeddings exceeds Vercel's 45-minute remote
build limit, deployment first packages the locally verified Chroma index and
extracted MiniLM model into two ignored runtime archives. `Dockerfile.vercel`
unpacks and validates those archives before the deployment receives traffic.

```bash
vercel login
vercel link
vercel project update --framework container --yes
make vercel-package       # verify/build locally, then create ignored archives
vercel deploy                                      # preview
# Test the preview URL, including /health and /api/search.
vercel deploy --prod --skip-domain                 # staged production
# Test the staged production URL, then promote that exact deployment.
vercel promote <tested-production-url>
```

The first `make vercel-package` run downloads the checksum-pinned CSV and MiniLM
model, creates all 32,392 embeddings, and validates the completed Chroma
collection. It writes `.vercel-artifacts/chroma.tar.gz` and
`.vercel-artifacts/model.tar.gz`; both are ignored by Git, while `.vercelignore`
allows the CLI to upload them as Docker build inputs. The raw CSV is not included
in either archive. A remote build only installs locked dependencies, extracts
the two archives, and revalidates their metadata and record count. A production
request never downloads data or builds embeddings.

During a cold start, Rift Index copies the image's verified Chroma directory to
a revision-specific location under writable `/tmp`, opens that copy with
`PersistentClient`, and reuses it for the warm container instance. Vercel
containers listen on `${PORT:-80}`, scale to zero when idle, and retain the same
Function memory and duration limits. See [Vercel's Container Runtime
documentation](https://vercel.com/docs/functions/runtimes/container) for current
platform behavior and limits.

## Commands

```bash
make run             # prepare data/index and launch the development server
make ingest          # idempotently prepare the index
make rebuild         # replace the local index
make verify-source   # checksum and count verification; no model download
make vercel-package  # create ignored, validated Vercel runtime archives
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
image build. Vercel deployment tests additionally validate bundle paths, model
archive pruning, exact index readiness, and read-only runtime preparation.
Generated datasets, model files, and indexes are never committed.

## Attribution and license

Application code is MIT licensed; see [LICENSE](LICENSE). The upstream dataset
is also MIT licensed by Allan Cao, and its exact notice is retained in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The upstream project states
that the transcripts were cleaned from League of Legends Wiki data.

League of Legends, its champions, trademarks, and voice-line text belong to
Riot Games and their respective rights holders. Rift Index is not affiliated with Riot Games
and is not endorsed by Riot Games.

The development prompt record is in [AI_PROMPT_LOG.md](AI_PROMPT_LOG.md).

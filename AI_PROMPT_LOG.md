# AI prompt log

This is the user-authored prompt record for Rift Index's initial version and
deployment. Entries are dated and reproduced verbatim. Credentials, hidden
instructions, tool output, and internal reasoning are intentionally excluded.

## 2026-10-25 — Initial request

> Using python with chroma DB, create a website that uses a vector database to find similar voicelines in league of legends (for example, user should be able to say find me voicelines talking about food). Create a github repository containing the code, a readme, and an AI prompt log. Find a dataset online to use

## 2026-10-25 — Interface choice

> option B is better

## 2026-10-25 — Approved implementation plan

> PLEASE IMPLEMENT THIS PLAN:
> # Rift Index Implementation Plan
>
> ## Summary
>
> Create a new public repository at `ryanwon3/rift-index`, separate from LaneDiff. Build a local-first Python 3.11 website using FastAPI, Jinja, vanilla JavaScript, and persistent Chroma storage. The selected “Champion Codex” interface will support semantic voice-line search, champion browsing, and line-type filtering without paid APIs or audio playback.
>
> ## Implementation Changes
>
> - Scaffold `/Users/moon/rift-index` with pinned dependencies, MIT code license, Dockerfile, Compose configuration, Make targets, `.gitignore`, and GitHub Actions. Re-authenticate GitHub CLI as `ryanwon3` before creating and pushing the public repository.
> - Pin the [Allan-Cao voice-line dataset](https://github.com/Allan-Cao/lol-voice-lines) at commit `85f70fb891f2471eda8a7a773479106b0d3bf88f`. Verify SHA-256 `a183f3a540bdee0299bdf58b732520a8f0acfc3baee10654c658048708a230b8` and expected totals: 32,392 rows, 163 champions, 31,240 spoken lines, and 1,152 actions. Retain the upstream [MIT notice](https://github.com/Allan-Cao/lol-voice-lines/blob/main/LICENSE) and Riot/Wiki attribution.
> - Implement idempotent ingestion with deterministic record IDs, batched Chroma upserts, source/model metadata, and `--rebuild`. Keep the downloaded CSV, embedding cache, and generated Chroma index outside Git.
> - Use Chroma `PersistentClient`, a pinned local `all-MiniLM-L6-v2` embedding function, and cosine distance. Existing indexes with mismatched source or model metadata must fail with a rebuild instruction rather than mix incompatible records. This follows Chroma’s documented local persistence model.
> - Build responsive Explore, Champions, and About pages matching Option B: persistent navigation, natural-language search, champion and `spoken/action/all` filters, ranked result cards, loading/error/empty states, keyboard accessibility, and mobile reflow.
> - Add a comprehensive README covering Python and Docker startup, first-run downloads, architecture, dataset coverage limitations, troubleshooting, attribution, and non-affiliation with Riot.
> - Add `AI_PROMPT_LOG.md` containing dated, verbatim user prompts and choice selections used to create the application. Exclude AI responses, system instructions, hidden reasoning, credentials, and tool output.
>
> ## Public Interfaces
>
> - `GET /api/search?q=<2–200 chars>&champion=<optional>&line_type=spoken|action|all&limit=1–50`
>   - Defaults: `line_type=spoken`, `limit=12`.
>   - Returns query metadata and `{id, champion, text, is_spoken, similarity}` results.
>   - Similarity is clamped cosine similarity and labeled as a ranking signal, not confidence.
> - `GET /api/champions` returns alphabetized champions with spoken/action counts.
> - `GET /health` returns service status, index readiness, record count, source revision, and embedding model; unavailable indexes produce HTTP 503 from search.
> - `python -m app.ingest [--rebuild]` verifies and builds the index.
> - `make run` prepares missing local dependencies/data and launches the app; `docker compose up --build` provides the container workflow.
>
> ## Test Plan
>
> - Test BOM-safe CSV parsing, required columns, checksum rejection, deterministic IDs, exact pinned-source counts, batching, idempotency, and explicit rebuild behavior.
> - Test Chroma persistence, cosine ranking, champion/type filters, and a real-model fixture where a food query returns food-related lines.
> - Test API validation for blank, oversized, malformed, unknown-champion, no-result, and unavailable-index requests.
> - Test server-rendered routes, safe quote rendering, URL-synchronized filters, and responsive desktop/mobile flows.
> - CI runs formatting/lint checks, pytest, pinned-source verification, and a Docker image build. Because Docker is unavailable on the current host, the GitHub Actions build is the authoritative container verification.
>
> ## Assumptions
>
> - Version one is English, transcript-only, unauthenticated, local-first, and not publicly deployed.
> - The pinned snapshot is intentionally historical; live Wiki scraping and automatic freshness updates are excluded.
> - Audio, champion artwork, analytics, accounts, and user-submitted data are excluded.
> - First run requires internet access to download the pinned CSV and embedding model; subsequent searches use local persisted files.
> - GitHub CLI’s saved credentials are currently expired, so implementation pauses only for the required `ryanwon3` browser re-authentication.

## 2026-10-27 — Deployment request

> deploy the website on vercel

## 2026-10-27 — Deployment approach approval

> sure, after youre done give me the vercel link and github link

## 2026-10-27 — Implementation request

> impliment

## 2026-10-27 — Deployment plan approval

> yes

## 2026-10-27 — README requirements

> continue, In the readme include:&#x20;
>
> - What your app does and why you chose it (1–2 sentences)
> - What you store in the database: where the data came from, what counts as one item, how you broke it up if you did, roughly how many items you loaded, and what metadata (if any) you attach to each one
> - How a user adds new items, and how a user searches
> - **Your two queries from the test above,** the items they retrieve, and why a keyword search would miss them
> - How we would obtain and load the data ourselves, since the raw dataset shouldn't be committed to your repo
> - Which vector database and embedding model you used, and whether anything downloads on first run
> - How to run your app (what to install, what commands to use)
>
> Before updating, give me the planned readme for me to edit

## 2026-10-27 — README approval

> looks good, continue

## 2026-10-28 — Container-runtime approval

> yes

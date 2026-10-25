# Rift Index Design

Rift Index is a public, local-first semantic search site for League of Legends voice-line transcripts. It uses Python 3.11, FastAPI, Jinja, vanilla JavaScript, persistent Chroma storage, and local `all-MiniLM-L6-v2` embeddings. The UI follows the approved Champion Codex direction: persistent navigation, natural-language search, champion browsing, and spoken/action filters.

The source is Allan Cao's `lol-voice-lines` CSV pinned at commit `85f70fb891f2471eda8a7a773479106b0d3bf88f`, SHA-256 `a183f3a540bdee0299bdf58b732520a8f0acfc3baee10654c658048708a230b8`. Expected contents are 32,392 rows across 163 champions: 31,240 spoken lines and 1,152 actions. The raw CSV, model cache, and Chroma index remain generated local data and are not committed.

The app provides Explore, Champions, and About views plus `/api/search`, `/api/champions`, and `/health`. Search accepts a 2–200 character query, optional exact champion, `spoken|action|all`, and a result limit from 1–50. Results expose champion, transcript, line type, and clamped cosine similarity as a ranking signal rather than confidence.

The repository is public under `ryanwon3/rift-index`, uses an MIT license for project code, attributes the upstream dataset and League Wiki, and states that Riot owns League of Legends and its voice lines. It includes Docker and local Make workflows, CI, a comprehensive README, and a prompt-only AI creation log. Audio, accounts, analytics, live scraping, public hosting, artwork, and user submissions are out of scope.


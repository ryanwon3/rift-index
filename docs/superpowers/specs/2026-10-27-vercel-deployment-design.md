# Vercel Deployment Design

## Intent

Publish Rift Index as a public Vercel site while preserving its FastAPI, local
MiniLM embedding, and Chroma-based semantic search architecture. The deployed
site should require no paid inference API and should expose the same pages and
API behavior as the local application.

## Goals

- Deploy the current `main` branch to a new Vercel project owned by the user.
- Keep the pinned voice-line dataset, deterministic Chroma index, and local
  `all-MiniLM-L6-v2` query embedding model.
- Make deployments reproducible from the GitHub repository and pinned source
  without committing generated data, model weights, or the Chroma index to Git.
- Verify the preview deployment end to end before promoting it to production.
- Return both the production Vercel URL and GitHub repository URL.

## Non-goals and anti-goals

- Do not replace Chroma with another vector database or use a paid embedding API.
- Do not add accounts, analytics, audio, or unrelated application features.
- Do not depend on durable writes to a Vercel Function filesystem.
- Do not publish an unverified production deployment.

## Constraints

- Vercel containers expose an immutable application image and writable `/tmp`
  scratch area. Rift Index copies Chroma's SQLite and HNSW files once per warm
  container before opening them.
- The generated index is about 90 MB and the extracted ONNX model is about 87 MB;
  they are split into separate ignored deployment archives below Vercel's
  per-file upload ceiling.
- A clean remote build that generated all 32,392 embeddings reached Vercel's
  45-minute build timeout. Embeddings must therefore be generated and validated
  before the CLI upload; the remote build only extracts and verifies them.

## Approaches considered

1. **Self-contained native Python Function.** This preserved the existing
   architecture, but query-time ONNX execution terminated the native process in
   production after multiple runtime hypotheses were tested and disproved.
2. **Container image with prebuilt runtime artifacts (selected).** Validate and
   archive the local Chroma index and extracted model, then unpack and revalidate
   them in `Dockerfile.vercel`. This preserves local inference without another
   service. Its tradeoffs are larger uploads/images and container cold starts.
3. **Hosted Chroma.** Use an external Chroma service. This produces a smaller,
   faster function but introduces credentials, an additional service, and
   possible cost, contrary to the local-first project goal.

## Deployment shape

- Use `Dockerfile.vercel` to install locked Python 3.11 dependencies, extract
  ignored deployment artifacts, validate the record count/metadata, and run a
  real 384-dimensional embedding smoke test before the image is accepted.
- Add a packaging module that validates the local index and model, archives only
  the Chroma index and extracted `onnx/` directory, and excludes the raw CSV and
  redundant model download archive.
- Add an embedding-function factory so local development continues using the
  normal cache while Vercel uses the bundled extracted ONNX files.
- At Vercel runtime, copy the bundled Chroma directory once per function instance
  into a revision-specific `/tmp` directory before creating `PersistentClient`.
- Add `.vercelignore` so the CLI uploads the ignored runtime archives while
  excluding local caches, tests, and development files.
- Keep `.data`, model caches, Vercel output, and project-link metadata outside Git.

## Verification and release

- Add tests for path selection, build validation, `/tmp` copy behavior, and local
  behavior remaining unchanged.
- Run Ruff, the complete pytest suite, and the existing pinned-source check.
- Link a new Vercel project only after confirming the authenticated owner and
  project target.
- Deploy a protected preview, test `/`, `/health`, `/api/champions`, and a real
  food-related `/api/search` request, then stage/promote that tested deployment
  to production.
- Inspect post-deployment runtime errors and confirm the production URL before
  reporting completion.

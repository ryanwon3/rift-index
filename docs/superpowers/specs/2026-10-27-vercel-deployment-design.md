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
- Make deployments reproducible from the GitHub repository without committing
  generated data, model weights, or the Chroma index to Git.
- Verify the preview deployment end to end before promoting it to production.
- Return both the production Vercel URL and GitHub repository URL.

## Non-goals and anti-goals

- Do not replace Chroma with another vector database or use a paid embedding API.
- Do not add accounts, analytics, audio, or unrelated application features.
- Do not depend on durable writes to a Vercel Function filesystem.
- Do not publish an unverified production deployment.

## Constraints

- Vercel Functions have a read-only application filesystem and a writable `/tmp`
  scratch area. Chroma's SQLite and HNSW files therefore cannot be opened in
  place from the bundled application.
- The generated index is about 90 MB and the extracted ONNX model is about 87 MB;
  the complete Python function may use Vercel's Large Functions path.
- The first remote build must download and verify the pinned dataset and model,
  then generate 32,392 embeddings. The observed local build time is about
  15 minutes, within Vercel's 45-minute build limit.

## Approaches considered

1. **Self-contained native Python Function (selected).** Generate the index and
   model during the Vercel build, bundle them as read-only assets, copy the Chroma
   index into `/tmp` during function initialization, and query it locally. This
   preserves the existing architecture without another service, at the cost of a
   larger bundle and cold start.
2. **Container image.** Build the application and index into `Dockerfile.vercel`.
   This is close to the current Docker workflow but adds container cold-start
   overhead and does not remove the ephemeral-filesystem constraint.
3. **Hosted Chroma.** Use an external Chroma service. This produces a smaller,
   faster function but introduces credentials, an additional service, and
   possible cost, contrary to the local-first project goal.

## Deployment shape

- Keep `app/main.py` as the Vercel-detected FastAPI entrypoint.
- Add a Vercel build module that runs the existing verified ingestion pipeline,
  stores deployment data under generated Vercel-only directories, removes the
  redundant downloaded model archive, and validates the finished index.
- Add an embedding-function factory so local development continues using the
  normal cache while Vercel uses the bundled extracted ONNX files.
- At Vercel runtime, copy the bundled Chroma directory once per function instance
  into a revision-specific `/tmp` directory before creating `PersistentClient`.
- Add `vercel.json` to include generated data/model assets, exclude development
  files, and set an appropriate initialization duration.
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

FROM ghcr.io/astral-sh/uv:0.13.5 AS uv
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    RIFT_INDEX_DATA_DIR=/app/.data \
    RIFT_INDEX_CACHE_DIR=/app/.cache

COPY --from=uv /uv /uvx /bin/

RUN useradd --create-home --uid 10001 rift
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN mkdir -p /app/.data /app/.cache && chown -R rift:rift /app

USER rift
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["sh", "-c", "uv run --no-sync python -m app.ingest && exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000"]

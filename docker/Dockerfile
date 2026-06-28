# Build from the repository root:
#   docker build -f docker/Dockerfile -t portfolio .
#
# Application code is mounted at runtime (see docker-compose.yml).
# Run via compose or ./bin/api.sh and ./bin/job.sh.

FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY docker/entrypoint.sh /app/docker/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p data \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["api"]

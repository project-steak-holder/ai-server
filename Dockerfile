# 1: Build Stage
FROM ghcr.io/astral-sh/uv:0.10.6-python3.14-trixie-slim@sha256:afdc829233119f8bb7ffc68839aaac57b3a4eda72947b2317ad218138fbd955a AS builder


WORKDIR /app

# Enable bytecode compilation and use copy link mode for performance
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# Copy source and install project (cached layer)
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# 2: Run Stage
FROM ghcr.io/astral-sh/uv:0.10.6-python3.14-trixie-slim@sha256:afdc829233119f8bb7ffc68839aaac57b3a4eda72947b2317ad218138fbd955a AS runner

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code (cached layers)
COPY --from=builder /app/src /app/src
COPY --from=builder /app/data /app/data
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/README.md /app/README.md

# Set environment variables
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system appgroup
RUN adduser --system --ingroup appgroup appuser

# Fix file ownership for runtime paths
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Start FastAPI app with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install project into a local prefix we can copy into the runtime image.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --prefix=/install .

# ── runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app && useradd --system --gid app --home /app --shell /usr/sbin/nologin app
WORKDIR /app

COPY --from=build /install /usr/local

USER app
ENTRYPOINT ["codi"]

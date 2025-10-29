FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    pkg-config \
    libcairo2-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY ./nodes /nodes
COPY ./node_runner /node_runner
COPY ./nodes_agno /nodes_agno
COPY ./nodes_dev /nodes_dev
COPY ./api-local/pyproject.toml ./
COPY ./api-local/poetry.lock ./

ENV POETRY_VIRTUALENVS_CREATE=false

# Clean all caches to prevent conflicts
RUN rm -rf /root/.cache/pypoetry/* && \
    rm -rf /root/.cache/pip/* && \
    pip cache purge || true

# Install dependencies using locked versions
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

# Verify installed versions for debugging
RUN echo "=== Installed package versions ===" && \
    poetry show agno || echo "agno not found via poetry" && \
    pip show agno || echo "agno not found via pip"

COPY ./api-local /app

# Set default reload directories (can be overridden by docker-compose)
ENV RELOAD_DIRS="--reload-dir /app"

EXPOSE 8090

# Use startup script to load secrets and start server
# Using sh -c to avoid permission issues with volume mounts
CMD ["sh", "/app/startup.sh"]
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY ./nodes /nodes
COPY ./node_runner /node_runner
COPY ./nodes_agno /nodes_agno
COPY ./api-local/pyproject.toml ./api-local/poetry.lock ./

ENV POETRY_VIRTUALENVS_CREATE=false

RUN rm -rf /root/.cache/pypoetry/*
RUN poetry lock && poetry install --no-interaction --no-ansi

COPY ./api-local /app

EXPOSE 8090

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--reload"]
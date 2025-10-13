#!/bin/bash
set -e

echo "🚀 Starting PolySynergy API..."

# Read Redis password from Docker secret if it exists
if [ -f /run/secrets/redis_password ]; then
    REDIS_PASSWORD=$(cat /run/secrets/redis_password)
    export REDIS_URL="redis://:${REDIS_PASSWORD}@redis:6379"
    echo "✓ Redis password loaded from Docker secret"
    echo "✓ REDIS_URL configured: redis://:*****@redis:6379"
else
    # Fallback to environment variable or default (for local development)
    if [ -z "$REDIS_URL" ]; then
        export REDIS_URL="redis://redis:6379"
        echo "⚠ No Redis secret found, using default: redis://redis:6379"
    else
        echo "✓ Using REDIS_URL from environment"
    fi
fi

# Read PostgreSQL password from Docker secret if it exists
if [ -f "$POSTGRES_PASSWORD_FILE" ]; then
    export POSTGRES_PASSWORD=$(cat "$POSTGRES_PASSWORD_FILE")
    echo "✓ PostgreSQL password loaded from secret"
fi

# Read Agno PostgreSQL password from Docker secret if it exists
if [ -f "$AGNO_POSTGRES_PASSWORD_FILE" ]; then
    export AGNO_POSTGRES_PASSWORD=$(cat "$AGNO_POSTGRES_PASSWORD_FILE")
    echo "✓ Agno PostgreSQL password loaded from secret"
fi

echo "🌐 Starting uvicorn server..."

# Start uvicorn with reload support
exec poetry run uvicorn main:app --host 0.0.0.0 --port 8090 --reload ${RELOAD_DIRS}

#!/bin/sh
set -e

echo "🚀 Starting PolySynergy API..."

# Use REDIS_URL from environment (.env file) - DO NOT override it
# The .env file contains the correct production Redis URL
if [ -z "$REDIS_URL" ]; then
    echo "⚠ WARNING: REDIS_URL not set in environment"
    # Only set default if truly empty (local dev without .env)
    if [ -f /run/secrets/redis_password ]; then
        REDIS_PASSWORD=$(cat /run/secrets/redis_password)
        export REDIS_URL="redis://:${REDIS_PASSWORD}@redis:6379"
        echo "✓ Using Docker secret for Redis password"
    else
        export REDIS_URL="redis://redis:6379"
        echo "⚠ Using default Redis URL (no auth)"
    fi
else
    echo "✓ Using REDIS_URL from environment: ${REDIS_URL}"
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

# Read Sections PostgreSQL password from Docker secret if it exists
if [ -f "$SECTIONS_POSTGRES_PASSWORD_FILE" ]; then
    export SECTIONS_DB_PASSWORD=$(cat "$SECTIONS_POSTGRES_PASSWORD_FILE")
    echo "✓ Sections PostgreSQL password loaded from secret"

    # Set other SECTIONS_DB_* variables if not already set (for Settings class)
    export SECTIONS_DB_NAME="${SECTIONS_DB_NAME:-sections_db}"
    export SECTIONS_DB_USER="${SECTIONS_DB_USER:-sections_user}"
    export SECTIONS_DB_HOST="${SECTIONS_DB_HOST:-sections_db}"
    export SECTIONS_DB_PORT="${SECTIONS_DB_PORT:-5432}"
fi

# Auto-install node packages that are mounted but not yet installed
# Scans NODE_PACKAGES for packages with a pyproject.toml at their mount point
if [ -n "$NODE_PACKAGES" ]; then
    echo "📦 Checking for additional node packages..."
    OLD_IFS="$IFS"
    IFS=','
    for pkg in $NODE_PACKAGES; do
        IFS="$OLD_IFS"
        pkg=$(echo "$pkg" | xargs)  # trim whitespace
        mount_path="/$pkg"
        if [ -f "$mount_path/pyproject.toml" ] && ! pip show "$pkg" > /dev/null 2>&1; then
            echo "📦 Installing $pkg from $mount_path..."
            pip install "$mount_path" || echo "⚠ Failed to install $pkg"
        fi
    done
fi

if [ -f "/possession/pyproject.toml" ] && ! pip show possession > /dev/null 2>&1; then
    echo "📦 Installing possession library from /possession..."
    pip install -e /possession || echo "⚠ Failed to install possession"
fi

if ! pip show claude-agent-sdk > /dev/null 2>&1; then
    echo "📦 Installing claude-agent-sdk..."
    pip install claude-agent-sdk || echo "⚠ Failed to install claude-agent-sdk"
fi

echo "🌐 Starting uvicorn server..."

# Start uvicorn with reload support
exec poetry run uvicorn main:app --host 0.0.0.0 --port 8090 --reload ${RELOAD_DIRS}

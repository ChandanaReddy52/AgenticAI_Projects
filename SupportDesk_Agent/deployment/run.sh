#!/bin/bash
# run.sh — Single entry point for SupportDesk Agent
# Usage: ./deployment/run.sh [--phase N] [--query "..."] [--eval]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "SupportDesk Agent — starting from $PROJECT_DIR"

# Activate virtual environment if present
if [ -f "$PROJECT_DIR/../.venv/Scripts/activate" ]; then
    source "$PROJECT_DIR/../.venv/Scripts/activate"
elif [ -f "$PROJECT_DIR/../.venv/bin/activate" ]; then
    source "$PROJECT_DIR/../.venv/bin/activate"
fi

# Load .env by walking up directory tree
ENV_FILE=""
SEARCH_DIR="$PROJECT_DIR"
for i in 1 2 3 4 5 6; do
    if [ -f "$SEARCH_DIR/.env" ]; then
        ENV_FILE="$SEARCH_DIR/.env"
        break
    fi
    SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

if [ -n "$ENV_FILE" ]; then
    echo "Loading environment from: $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "WARNING: No .env file found — OPENAI_API_KEY must be set"
fi

# Run health check
echo "Running health check..."
python "$PROJECT_DIR/deployment/health_check.py"
if [ $? -ne 0 ]; then
    echo "Health check failed. Fix errors above before proceeding."
    exit 1
fi

# Start agent
cd "$PROJECT_DIR"
python main.py "$@"
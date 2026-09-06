#!/usr/bin/env bash
set -e

# Change to the directory of this script
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

# Initialize virtual environment if not present
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install / update dependencies
echo "Checking and installing dependencies..."
pip install -r requirements.txt --quiet

echo "=================================================="
echo "Starting RPG Game Backend on http://0.0.0.0:${PORT}"
echo "Health check endpoint: http://0.0.0.0:${PORT}/healthz"
echo "API state endpoint:    http://0.0.0.0:${PORT}/api/state"
echo "=================================================="

exec uvicorn app:app --host 0.0.0.0 --port "${PORT}"

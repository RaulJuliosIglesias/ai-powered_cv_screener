#!/bin/bash
set -e

# Get the PORT from Railway environment (default to 8080)
PORT="${PORT:-8080}"

echo "Starting CV Screener on port $PORT..."
echo "Environment: CLOUD_ONLY_MODE=${CLOUD_ONLY_MODE:-false}"

# Start FastAPI with static file serving
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 30

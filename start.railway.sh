#!/bin/bash
set -e

# Get the PORT from Railway environment (default to 8000)
PORT="${PORT:-8000}"

echo "Starting CV Screener on port $PORT..."
echo "Environment: CLOUD_ONLY_MODE=${CLOUD_ONLY_MODE:-false}"

# Update nginx to listen on the correct port
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/sites-available/default

# Start nginx in background
nginx

# Wait a moment for nginx to start
sleep 2

# Start uvicorn backend with timeout prevention
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --timeout-keep-alive 30

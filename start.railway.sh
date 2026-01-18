#!/bin/bash
set -e

# Get the PORT from Railway environment (default to 8000)
PORT="${PORT:-8000}"

echo "Starting CV Screener on port $PORT..."

# Update nginx to listen on the correct port
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/sites-available/default

# Start nginx in background
nginx

# Start uvicorn backend (internal port 8000)
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2

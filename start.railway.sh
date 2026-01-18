#!/bin/bash
set -e

# Get the PORT from Railway environment (default to 8080)
PORT="${PORT:-8080}"

echo "Starting CV Screener on port $PORT..."
echo "Environment: CLOUD_ONLY_MODE=${CLOUD_ONLY_MODE:-false}"

# Create nginx config in conf.d (Debian/slim pattern)
mkdir -p /etc/nginx/conf.d
cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen 0.0.0.0:$PORT default_server;
    server_name _;

    access_log /dev/stdout;
    error_log /dev/stderr;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    location / {
        root /app/static;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Railway deployment check endpoint
    location /railway {
        return 200 "OK";
        add_header Content-Type text/plain;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        client_max_body_size 50M;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        root /app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test nginx config
echo "Testing nginx configuration..."
nginx -t

# Start uvicorn in background
echo "Starting uvicorn backend..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --timeout-keep-alive 30 &
UVICORN_PID=$!

# Wait for uvicorn to be ready
echo "Waiting for backend to be ready..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "WARNING: Backend not ready after 10 seconds"
    fi
    sleep 1
done

echo "Starting nginx on port $PORT..."
exec nginx -g 'daemon off;'

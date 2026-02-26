#!/bin/bash
PORT=${PORT:-5000}

cleanup_port() {
    if fuser "$PORT/tcp" >/dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Port $PORT in use, cleaning up..."
        fuser -k "$PORT/tcp" >/dev/null 2>&1
        sleep 2
    fi
}

trap 'echo "$(date "+%Y-%m-%d %H:%M:%S") [INFO] Shutting down..."; kill %1 2>/dev/null; exit 0' SIGTERM SIGINT

while true; do
    cleanup_port
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Starting server on port $PORT..."
    python app.py
    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Server exited (code=$EXIT_CODE), restarting in 3s..."
    sleep 3
done

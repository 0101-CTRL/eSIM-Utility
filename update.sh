#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/api-v3-esim-ui}"
SERVICE_NAME="${SERVICE_NAME:-api-v3-esim-ui}"

cd "$APP_DIR"

echo "=== eSIM Utility Update ==="
echo "App directory: $APP_DIR"
echo "Service: $SERVICE_NAME"
echo

echo "Current version:"
cat VERSION 2>/dev/null || echo "unknown"

echo
echo "Current commit:"
git rev-parse --short HEAD || true

echo
echo "Checking working tree..."
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: Working tree has local changes."
  echo "Commit, stash, or discard local changes before updating."
  git status --short
  exit 1
fi

echo
echo "Backing up current app.py..."
mkdir -p backups
cp app.py "backups/app.py.pre-update.$(date +%Y%m%d-%H%M%S)"

echo
echo "Fetching latest changes..."
git fetch origin main

echo
echo "Pulling latest main branch..."
git pull --ff-only origin main

echo
echo "Installing/updating dependencies..."
if [ -f requirements.txt ]; then
  ./venv/bin/pip install -r requirements.txt
else
  ./venv/bin/pip install fastapi "uvicorn[standard]" httpx python-multipart
fi

echo
echo "Checking Python syntax..."
./venv/bin/python -m py_compile app.py

echo
echo "Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

echo
echo "Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo
echo "Updated version:"
cat VERSION 2>/dev/null || echo "unknown"

echo
echo "Updated commit:"
git rev-parse --short HEAD || true

echo
echo "Update complete."

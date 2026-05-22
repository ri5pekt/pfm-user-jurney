#!/usr/bin/env bash
# deploy.sh — pull latest code and rebuild containers on the VPS
# Usage: bash scripts/deploy.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="docker-compose.yml"

echo "==> Pulling latest code..."
cd "$REPO_DIR"
git pull origin main

echo "==> Building and restarting containers..."
docker compose -f "$COMPOSE_FILE" build --no-cache
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Cleaning up dangling images..."
docker image prune -f

echo "==> Deploy complete."
docker compose -f "$COMPOSE_FILE" ps

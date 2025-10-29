#!/usr/bin/env bash
set -euo pipefail
# Small convenience wrapper so docker-compose always loads the repo `.env`.
# Usage: ./docker/up.sh up -d --build

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Compose file lives in the same directory as this script.
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Warning: env file not found at $ENV_FILE"
fi

docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"

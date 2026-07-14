#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/../../.." && pwd)
if ! docker inspect haintly-db-vacancy haintly-redis >/dev/null 2>&1; then
  echo "Поднимите тестовую инфраструктуру командой: make infra" >&2
  exit 1
fi
set -a
. "$root/.docker-compose/.env"
set +a
redis_password=$(docker inspect haintly-redis --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^REDIS_PASSWORD=//p')
POSTGRES_HOST=localhost POSTGRES_PORT="$VACANCY_POSTGRES_EXP_PORT" \
POSTGRES_USER="$VACANCY_POSTGRES_USER" POSTGRES_PASSWORD="$VACANCY_POSTGRES_PASSWORD" \
POSTGRES_DB="$VACANCY_POSTGRES_DB" \
DICTIONARY_LOCK_URL="redis://:${redis_password}@localhost:${REDIS_PORT:-6379}/4" \
uv run pytest

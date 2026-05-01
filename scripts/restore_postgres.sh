#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <service: auth|event|booking> <backup_file.dump>"
  exit 1
fi

SERVICE="$1"
BACKUP_FILE="$2"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

if [[ -f .env ]]; then
 source .env
else
  echo "Missing .env file in project root"
  exit 1
fi

resolve_container() {
  local suffix="$1"
  docker ps --format '{{.Names}}' | awk -v s="$suffix" '$0 ~ s"$" {print; exit}'
}

case "$SERVICE" in
  auth)
    CONTAINER_SUFFIX="booking_postgres_auth"
    DB_USER="$AUTH_POSTGRES_USER"
    DB_PASSWORD="$AUTH_POSTGRES_PASSWORD"
    DB_NAME="$AUTH_POSTGRES_DB"
    ;;
  event)
    CONTAINER_SUFFIX="booking_postgres_event"
    DB_USER="$EVENT_POSTGRES_USER"
    DB_PASSWORD="$EVENT_POSTGRES_PASSWORD"
    DB_NAME="$EVENT_POSTGRES_DB"
    ;;
  booking)
    CONTAINER_SUFFIX="booking_postgres_booking"
    DB_USER="$BOOKING_POSTGRES_USER"
    DB_PASSWORD="$BOOKING_POSTGRES_PASSWORD"
    DB_NAME="$BOOKING_POSTGRES_DB"
    ;;
  *)
    echo "Unknown service: $SERVICE. Use auth, event, or booking."
    exit 1
    ;;
esac

CONTAINER="$(resolve_container "$CONTAINER_SUFFIX")"

if [[ -z "$CONTAINER" ]]; then
  echo "Container not found for service '$SERVICE' (suffix: $CONTAINER_SUFFIX)"
  exit 1
fi

running="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
if [[ "$running" != "true" ]]; then
  echo "Container is not running: $CONTAINER"
  exit 1
fi

echo "Restoring $SERVICE database from $BACKUP_FILE into container $CONTAINER..."

docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges \
  < "$BACKUP_FILE"

echo "Restore completed for $SERVICE"
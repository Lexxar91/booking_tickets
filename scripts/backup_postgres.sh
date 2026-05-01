#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  source .env

else
  echo "Missing .env file in project root"
  exit 1

fi 


BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups/postgres}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$BACKUP_ROOT/$TS"

mkdir -p "$RUN_DIR"


resolve_container() {
  local suffix="$1"
  docker ps --format '{{.Names}}' | awk -v s="$suffix" '$0 ~ s"$" {print; exit}'
}


AUTH_CONTAINER="$(resolve_container "booking_postgres_auth")"
EVENT_CONTAINER="$(resolve_container "booking_postgres_event")"
BOOKING_CONTAINER="$(resolve_container "booking_postgres_booking")"

[[ -n "$AUTH_CONTAINER" ]] || { echo "Auth DB container not found"; exit 1; }
[[ -n "$EVENT_CONTAINER" ]] || { echo "Event DB container not found"; exit 1; }
[[ -n "$BOOKING_CONTAINER" ]] || { echo "Booking DB container not found"; exit 1; }


dump_one() {
  local container_name="$1"
  local db_user="$2"
  local db_password="$3"
  local db_name="$4"
  local output_name="$5"

  echo "Backing up $output_name..."
  docker exec -e PGPASSWORD="${!db_password}" "$container_name" \
    pg_dump -U "${!db_user}" -d "${!db_name}" -Fc > "$RUN_DIR/$output_name.dump"
}


dump_one "$AUTH_CONTAINER" "AUTH_POSTGRES_USER" "AUTH_POSTGRES_PASSWORD" "AUTH_POSTGRES_DB" "auth"
dump_one "$EVENT_CONTAINER" "EVENT_POSTGRES_USER" "EVENT_POSTGRES_PASSWORD" "EVENT_POSTGRES_DB" "event"
dump_one "$BOOKING_CONTAINER" "BOOKING_POSTGRES_USER" "BOOKING_POSTGRES_PASSWORD" "BOOKING_POSTGRES_DB" "booking"


find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$BACKUP_RETENTION_DAYS" -exec rm -rf {} +

echo "Backup completed: $RUN_DIR"
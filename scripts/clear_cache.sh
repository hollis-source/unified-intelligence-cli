#!/usr/bin/env bash
set -euo pipefail

# Safe Redis cache clear for development
# - Deletes keys by namespace using SCAN+DEL
# - FLUSHDB only allowed in dev with interactive confirmation
#
# Usage:
#   scripts/clear_cache.sh [--namespace PREFIX] [--redis-url URL] [--danger-flushdb]
#
# Env:
#   ATADO_ENV                Environment name (default: dev)
#   ATADO_CACHE_NAMESPACE    Namespace prefix for keys (e.g., atado:dev:llm:response:)
#   REDIS_URL                redis://host:port/db (default: redis://localhost:6379/0)

ATADO_ENV=${ATADO_ENV:-dev}
NAMESPACE=""
REDIS_URL=${REDIS_URL:-${2:-redis://localhost:6379/0}}
DANGER_FLUSH=0

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)
      NAMESPACE="$2"; shift 2 ;;
    --redis-url)
      REDIS_URL="$2"; shift 2 ;;
    --danger-flushdb)
      DANGER_FLUSH=1; shift ;;
    *)
      echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Compute default namespace if not provided
if [[ -z "$NAMESPACE" ]]; then
  if [[ -n "${ATADO_CACHE_NAMESPACE:-}" ]]; then
    NAMESPACE="$ATADO_CACHE_NAMESPACE"
  else
    NAMESPACE="atado:${ATADO_ENV}:llm:response:"
  fi
fi

# Require redis-cli
if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found. Please install Redis CLI." >&2
  exit 2
fi

# Extract redis-cli params from URL
# Expected: redis://host:port/db
proto_host_port_db="${REDIS_URL#redis://}"
host_port="${proto_host_port_db%/*}"
db="${proto_host_port_db##*/}"
host="${host_port%%:*}"
port="${host_port##*:}"

if [[ $DANGER_FLUSH -eq 1 ]]; then
  if [[ "$ATADO_ENV" != "dev" ]]; then
    echo "Refusing to FLUSHDB: ATADO_ENV=$ATADO_ENV (must be dev)" >&2
    exit 3
  fi
  echo "About to FLUSHDB on $host:$port db $db (dev only). Type YES to confirm:"
  read -r CONFIRM
  if [[ "$CONFIRM" != "YES" ]]; then
    echo "Aborted."; exit 0
  fi
  redis-cli -h "$host" -p "$port" -n "$db" FLUSHDB
  echo "FLUSHDB complete."
  exit 0
fi

# Namespaced delete using SCAN
echo "Clearing keys with prefix '$NAMESPACE*' on $host:$port db $db"
count=0
cursor=0
while :; do
  read -r cursor keys <<<"$(redis-cli -h "$host" -p "$port" -n "$db" --raw SCAN "$cursor" MATCH "${NAMESPACE}*" COUNT 1000 | tr '\n' ' ' )"
  # The output parsing above is simplistic; perform a second scan to list keys
  mapfile -t batch < <(redis-cli -h "$host" -p "$port" -n "$db" --raw SCAN "$cursor" MATCH "${NAMESPACE}*" COUNT 1000 | tail -n +2)
  if [[ ${#batch[@]} -gt 0 ]]; then
    redis-cli -h "$host" -p "$port" -n "$db" DEL "${batch[@]}" >/dev/null || true
    count=$((count + ${#batch[@]}))
  fi
  [[ "$cursor" == "0" ]] && break
done

echo "Deleted $count keys with prefix '$NAMESPACE'"


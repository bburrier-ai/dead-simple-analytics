#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/apps/dead-simple-analytics}"
LOCK_FILE="${LOCK_FILE:-/tmp/dsa-watchdog.lock}"
APP_DOMAIN="${APP_DOMAIN:-stats.bburrier.com}"
HEALTH_RETRIES="${HEALTH_RETRIES:-12}"
HEALTH_RETRY_DELAY="${HEALTH_RETRY_DELAY:-5}"

fail() {
  printf 'DSA watchdog failed: %s\n' "$1" >&2
  exit 1
}

check_health() {
  local label="$1"
  local url="$2"
  local response
  local attempt

  for ((attempt = 1; attempt <= HEALTH_RETRIES; attempt++)); do
    if response="$(curl -fsS --connect-timeout 5 --max-time 15 "$url" 2>/dev/null)" \
      && [[ "$response" == *'"status":"ok"'* ]]; then
      return 0
    fi
    if (( attempt < HEALTH_RETRIES )); then
      sleep "$HEALTH_RETRY_DELAY"
    fi
  done

  fail "$label health check failed after $HEALTH_RETRIES attempts: $url"
}

for command in git make curl flock; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

cd "$REPO_DIR" || fail "repository is unavailable: $REPO_DIR"
[[ -d .git ]] || fail "Git repository missing: $REPO_DIR"
[[ -f .env ]] || fail "environment file missing: $REPO_DIR/.env"

set -a
# shellcheck source=/dev/null
source .env
set +a

if ! git checkout master >/dev/null 2>&1; then
  fail "cannot check out master in $REPO_DIR"
fi
if ! git fetch --prune origin master >/dev/null 2>&1; then
  fail "git fetch --prune origin master returned nonzero"
fi

local_sha="$(git rev-parse HEAD)" || fail "cannot resolve local HEAD"
remote_sha="$(git rev-parse origin/master)" || fail "cannot resolve origin/master"
[[ "$local_sha" == "$remote_sha" ]] && exit 0

if ! git merge-base --is-ancestor "$local_sha" "$remote_sha"; then
  fail "local master $local_sha cannot fast-forward to origin/master $remote_sha; reconcile manually"
fi

if ! git pull --ff-only origin master >/dev/null 2>&1; then
  fail "git pull --ff-only origin master returned nonzero"
fi
if ! make up >/dev/null 2>&1; then
  fail "make up returned nonzero at $remote_sha"
fi

host_port="${DSA_HOST_PORT:-8082}"
public_url="${PUBLIC_BASE_URL:-https://${APP_DOMAIN}}"
check_health "local" "http://127.0.0.1:${host_port}/api/healthz"
check_health "public" "${public_url%/}/api/healthz"

printf 'DSA watchdog deployed %s -> %s successfully\n' "$local_sha" "$remote_sha"

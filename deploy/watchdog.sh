#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-/opt/apps/dead-simple-analytics}"
APP_DOMAIN="${APP_DOMAIN:-stats.bburrier.com}"
STATE_DIR="${STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/dead-simple-analytics}"
HEALTH_RETRIES="${HEALTH_RETRIES:-6}"
HEALTH_RETRY_DELAY="${HEALTH_RETRY_DELAY:-3}"
readonly MAX_HEALTH_RETRIES=6
readonly MAX_HEALTH_RETRY_DELAY=3
readonly CURL_CONNECT_TIMEOUT=3
readonly CURL_MAX_TIME=8
readonly DNS_TIMEOUT=5
readonly TCP_TIMEOUT=3

if [[ "${DSA_WATCHDOG_MANAGED:-}" != 1 ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'DSA watchdog failed: required command missing: python3\n' >&2
    exit 1
  fi
  exec python3 "$SCRIPT_DIR/watchdog_state.py" "$STATE_DIR" /bin/bash "$0" "$@"
fi

WATCHDOG_EVIDENCE_PATH="${DSA_WATCHDOG_EVIDENCE_PATH:-}"
unset DSA_WATCHDOG_EVIDENCE_PATH
readonly WATCHDOG_EVIDENCE_PATH

bound_runtime_settings() {
  if [[ ! "$HEALTH_RETRIES" =~ ^[1-9][0-9]*$ ]] \
    || [[ ! "$HEALTH_RETRY_DELAY" =~ ^[0-9]+$ ]]; then
    fail "health retry settings must be non-negative integers with at least one retry"
  fi
  if (( HEALTH_RETRIES > MAX_HEALTH_RETRIES )); then
    HEALTH_RETRIES="$MAX_HEALTH_RETRIES"
  fi
  if (( HEALTH_RETRY_DELAY > MAX_HEALTH_RETRY_DELAY )); then
    HEALTH_RETRY_DELAY="$MAX_HEALTH_RETRY_DELAY"
  fi
}

fail() {
  local timestamp
  local message

  timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  message="DSA watchdog failed at ${timestamp}: $1"
  printf '%s\n' "$message" >&2
  if [[ -n "$WATCHDOG_EVIDENCE_PATH" ]]; then
    printf '%s\n' "$message" >>"$WATCHDOG_EVIDENCE_PATH" || true
  fi

  exit 1
}

check_health() {
  local label="$1"
  local url="$2"
  local expected_status="${3:-ok}"
  local response
  local attempt

  for ((attempt = 1; attempt <= HEALTH_RETRIES; attempt++)); do
    if response="$(curl -fsS --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" "$url" 2>/dev/null)" \
      && [[ "$response" == *"\"status\":\"${expected_status}\""* ]]; then
      return 0
    fi
    if (( attempt < HEALTH_RETRIES )); then
      sleep "$HEALTH_RETRY_DELAY"
    fi
  done

  fail "$label health check failed after $HEALTH_RETRIES attempts: $url"
}

check_http_status() {
  local label="$1"
  local expected_status="$2"
  local url="$3"
  local response
  local attempt

  for ((attempt = 1; attempt <= HEALTH_RETRIES; attempt++)); do
    if response="$(curl -sS --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)" \
      && [[ "$response" == "$expected_status" ]]; then
      return 0
    fi
    if (( attempt < HEALTH_RETRIES )); then
      sleep "$HEALTH_RETRY_DELAY"
    fi
  done

  fail "$label expected HTTP $expected_status after $HEALTH_RETRIES attempts: $url"
}

check_dns() {
  timeout "$DNS_TIMEOUT" getent ahostsv4 "$APP_DOMAIN" >/dev/null 2>&1 \
    || fail "dns lookup failed: $APP_DOMAIN"
}

check_tcp() {
  local port="$1"
  nc -z -w "$TCP_TIMEOUT" "$APP_DOMAIN" "$port" >/dev/null 2>&1 \
    || fail "tcp_${port} connection failed: $APP_DOMAIN:$port"
}

check_layers() {
  local host_port="${DSA_HOST_PORT:-8082}"
  local public_url="${PUBLIC_BASE_URL:-https://${APP_DOMAIN}}"

  check_dns
  check_tcp 80
  check_tcp 443
  check_health "app_health" "http://127.0.0.1:${host_port}/api/healthz"
  check_health "api_readiness" "http://127.0.0.1:${host_port}/api/readyz" ready
  check_http_status "proxy" 200 "${public_url%/}/login"
  check_health "public_health" "${public_url%/}/api/healthz"
  check_http_status "api_route" 401 "${public_url%/}/api/sites"
}

bound_runtime_settings

for command in git make curl getent nc timeout; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done

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
if [[ "$local_sha" == "$remote_sha" ]]; then
  check_layers
  exit 0
fi

if ! git merge-base --is-ancestor "$local_sha" "$remote_sha"; then
  fail "local master $local_sha cannot fast-forward to origin/master $remote_sha; reconcile manually"
fi

if ! git pull --ff-only origin master >/dev/null 2>&1; then
  fail "git pull --ff-only origin master returned nonzero"
fi
if ! make up >/dev/null 2>&1; then
  fail "make up returned nonzero at $remote_sha"
fi

check_layers

printf 'DSA watchdog deployed %s -> %s successfully\n' "$local_sha" "$remote_sha"

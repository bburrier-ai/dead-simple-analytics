#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG="${SCRIPT_DIR}/watchdog.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

mkdir -p "$TMP_DIR/bin" "$TMP_DIR/repo/.git"
touch "$TMP_DIR/repo/.env"

cat >"$TMP_DIR/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\n' "$*" >>"$COMMAND_LOG"
case "$1" in
  checkout|fetch|pull)
    [[ "${FAIL_STEP:-}" != "$1" ]]
    ;;
  rev-parse)
    case "$2" in
      HEAD) printf '%s\n' "$LOCAL_SHA" ;;
      origin/master) printf '%s\n' "$REMOTE_SHA" ;;
      *) exit 2 ;;
    esac
    ;;
  merge-base) exit "${MERGE_BASE_EXIT:-0}" ;;
  *) exit 2 ;;
esac
EOF

cat >"$TMP_DIR/bin/make" <<'EOF'
#!/usr/bin/env bash
printf '%s %s\n' "$(basename "$0")" "$*" >>"$COMMAND_LOG"
[[ "${FAIL_STEP:-}" != make ]]
EOF

cat >"$TMP_DIR/bin/curl" <<'EOF'
#!/usr/bin/env bash
printf 'curl %s\n' "$*" >>"$COMMAND_LOG"
[[ "${FAIL_STEP:-}" != health ]] || exit 22
printf '%s\n' '{"status":"ok"}'
EOF
chmod +x "$TMP_DIR/bin/"*

output_file="$TMP_DIR/output"
command_log="$TMP_DIR/commands"
if ! PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "no-op watchdog run returned nonzero"
fi

[[ ! -s "$output_file" ]] || fail "no-op watchdog run produced output"
! grep -q '^make ' "$command_log" || fail "no-op watchdog invoked make"

printf 'PASS: no-op watchdog run is silent\n'

: >"$output_file"
: >"$command_log"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  MERGE_BASE_EXIT=1 \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "diverged watchdog run returned zero"
fi

grep -q 'cannot fast-forward' "$output_file" || fail "divergence error is not actionable"
! grep -q 'reset' "$command_log" || fail "divergence path invoked git reset"

printf 'PASS: divergence fails without discarding history\n'

: >"$output_file"
: >"$command_log"
if ! PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "fast-forward deployment returned nonzero"
fi

grep -q '^git pull --ff-only origin master$' "$command_log" || fail "watchdog did not use pull --ff-only"
grep -q '^make up$' "$command_log" || fail "watchdog did not run make up"
[[ "$(grep -c '^curl ' "$command_log")" -eq 2 ]] || fail "watchdog did not run both health checks"

printf 'PASS: fast-forward update deploys and checks health\n'

for failure_case in fetch pull make health; do
  : >"$output_file"
  : >"$command_log"
  if PATH="$TMP_DIR/bin:$PATH" \
    COMMAND_LOG="$command_log" \
    LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    REMOTE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
    FAIL_STEP="$failure_case" \
    REPO_DIR="$TMP_DIR/repo" \
    LOCK_FILE="$TMP_DIR/watchdog.lock" \
    HEALTH_RETRIES=1 \
    bash "$WATCHDOG" >"$output_file" 2>&1; then
    fail "$failure_case failure returned zero"
  fi

  case "$failure_case" in
    fetch) expected='git fetch --prune origin master returned nonzero' ;;
    pull) expected='git pull --ff-only origin master returned nonzero' ;;
    make) expected='make up returned nonzero' ;;
    health) expected='health check failed' ;;
  esac
  grep -q "$expected" "$output_file" || fail "$failure_case failure is not actionable"
done

printf 'PASS: fetch, deploy, and health failures are actionable\n'

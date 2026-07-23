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
url="${*: -1}"
case "$url" in
  *127.0.0.1*healthz*) failure_case=app_health ;;
  *127.0.0.1*readyz*) failure_case=api_readiness ;;
  */login) failure_case=proxy ;;
  */api/sites) failure_case=api_route ;;
  *) failure_case=public_health ;;
esac
[[ "${FAIL_STEP:-}" != "$failure_case" ]] || exit 22
case "$url" in
  */login) printf '%s\n' '200' ;;
  */api/sites) printf '%s\n' '401' ;;
  *readyz*) printf '%s\n' '{"status":"ready"}' ;;
  *) printf '%s\n' '{"status":"ok"}' ;;
esac
EOF

cat >"$TMP_DIR/bin/getent" <<'EOF'
#!/usr/bin/env bash
printf 'getent %s\n' "$*" >>"$COMMAND_LOG"
[[ "${FAIL_STEP:-}" != dns ]] || exit 2
printf '%s\n' '192.0.2.1 STREAM stats.example.test'
EOF

cat >"$TMP_DIR/bin/nc" <<'EOF'
#!/usr/bin/env bash
printf 'nc %s\n' "$*" >>"$COMMAND_LOG"
port="${*: -1}"
[[ "${FAIL_STEP:-}" != "tcp_${port}" ]]
EOF
cat >"$TMP_DIR/bin/timeout" <<'EOF'
#!/usr/bin/env bash
printf 'timeout %s\n' "$*" >>"$COMMAND_LOG"
shift
exec "$@"
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
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "no-op watchdog run returned nonzero: $(<"$output_file")"
fi

[[ ! -s "$output_file" ]] || fail "no-op watchdog run produced output"
! grep -q '^make ' "$command_log" || fail "no-op watchdog invoked make"
[[ "$(grep -c '^getent ' "$command_log")" -eq 1 ]] || fail "no-op watchdog did not check DNS"
[[ "$(grep -c '^nc ' "$command_log")" -eq 2 ]] || fail "no-op watchdog did not check TCP 80 and 443"
[[ "$(grep -c '^curl ' "$command_log")" -eq 5 ]] || fail "no-op watchdog did not run layered HTTP/API checks"
[[ ! -e "$TMP_DIR/state/failures.log" ]] || fail "healthy no-op watchdog persisted failure evidence"
grep -q -- '--connect-timeout 3 --max-time 8' "$command_log" \
  || fail "HTTP checks do not use bounded request timeouts"
grep -q '^timeout 5 getent ' "$command_log" \
  || fail "DNS lookup is not bounded"

printf 'PASS: healthy no-op watchdog is silent and runs layered monitoring\n'

: >"$output_file"
: >"$command_log"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  MERGE_BASE_EXIT=1 \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  STATE_DIR="$TMP_DIR/state" \
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
  STATE_DIR="$TMP_DIR/state" \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "fast-forward deployment returned nonzero"
fi

grep -q '^git pull --ff-only origin master$' "$command_log" || fail "watchdog did not use pull --ff-only"
grep -q '^make up$' "$command_log" || fail "watchdog did not run make up"
[[ "$(grep -c '^curl ' "$command_log")" -eq 5 ]] || fail "watchdog did not run layered health checks"

printf 'PASS: fast-forward update deploys and checks health\n'

for failure_case in fetch pull make app_health; do
  : >"$output_file"
  : >"$command_log"
  if PATH="$TMP_DIR/bin:$PATH" \
    COMMAND_LOG="$command_log" \
    LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    REMOTE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
    FAIL_STEP="$failure_case" \
    REPO_DIR="$TMP_DIR/repo" \
    LOCK_FILE="$TMP_DIR/watchdog.lock" \
    STATE_DIR="$TMP_DIR/state" \
    HEALTH_RETRIES=1 \
    bash "$WATCHDOG" >"$output_file" 2>&1; then
    fail "$failure_case failure returned zero"
  fi

  case "$failure_case" in
    fetch) expected='git fetch --prune origin master returned nonzero' ;;
    pull) expected='git pull --ff-only origin master returned nonzero' ;;
    make) expected='make up returned nonzero' ;;
    app_health) expected='app_health health check failed' ;;
  esac
  grep -q "$expected" "$output_file" || fail "$failure_case failure is not actionable"
done

printf 'PASS: fetch, deploy, and app health failures are actionable\n'

for failure_case in dns tcp_80 tcp_443 app_health api_readiness proxy public_health api_route; do
  : >"$output_file"
  : >"$command_log"
  rm -f "$TMP_DIR/state/failures.log"
  if PATH="$TMP_DIR/bin:$PATH" \
    COMMAND_LOG="$command_log" \
    LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    FAIL_STEP="$failure_case" \
    REPO_DIR="$TMP_DIR/repo" \
    LOCK_FILE="$TMP_DIR/watchdog.lock" \
    STATE_DIR="$TMP_DIR/state" \
    APP_DOMAIN=stats.example.test \
    HEALTH_RETRIES=1 \
    bash "$WATCHDOG" >"$output_file" 2>&1; then
    fail "$failure_case monitoring failure returned zero"
  fi

  grep -q 'DSA watchdog failed at .*Z:' "$output_file" || fail "$failure_case output lacks UTC evidence"
  grep -q "$failure_case" "$output_file" || fail "$failure_case output is not classified"
  grep -q 'DSA watchdog failed at .*Z:' "$TMP_DIR/state/failures.log" || fail "$failure_case was not persisted"
done

printf 'PASS: layered monitoring failures are classified and persist UTC evidence\n'

printf 'old failure\n' >"$TMP_DIR/state/failures.log"
chmod 644 "$TMP_DIR/state/failures.log"
: >"$output_file"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  FAIL_STEP=dns \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "failure log permission scenario returned zero"
fi

[[ "$(stat -c '%a' "$TMP_DIR/state")" == 700 ]] || fail "watchdog state directory is not mode 0700"
[[ "$(stat -c '%a' "$TMP_DIR/state/failures.log")" == 600 ]] || fail "failure evidence log is not mode 0600"

printf 'PASS: persistent failure evidence has private permissions\n'

: >"$TMP_DIR/state/failures.log"
for ((line = 1; line <= 1000; line++)); do
  printf 'old failure %s\n' "$line" >>"$TMP_DIR/state/failures.log"
done
: >"$output_file"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  FAIL_STEP=dns \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "bounded failure log scenario returned zero"
fi

[[ "$(wc -l <"$TMP_DIR/state/failures.log")" -eq 1000 ]] || fail "failure evidence log exceeded 1000 lines"
grep -q 'DSA watchdog failed at .*Z: dns' "$TMP_DIR/state/failures.log" || fail "bounded failure log dropped newest evidence"

printf 'PASS: persistent failure evidence is bounded\n'

rm -rf "$TMP_DIR/state"
mkdir "$TMP_DIR/attacker-state"
ln -s "$TMP_DIR/attacker-state" "$TMP_DIR/state"
: >"$output_file"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "symlinked state directory was accepted"
fi

grep -q 'state directory is not a private owned directory' "$output_file" \
  || fail "symlinked state directory failure is not actionable"
[[ ! -e "$TMP_DIR/attacker-state/failures.log" ]] \
  || fail "watchdog wrote failure evidence through a state-directory symlink"

printf 'PASS: symlinked state directory is rejected\n'

: >"$output_file"
: >"$command_log"
rm -rf "$TMP_DIR/state"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  LOCK_FILE="$TMP_DIR/watchdog.lock" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  FAIL_STEP=app_health \
  HEALTH_RETRIES=999 \
  HEALTH_RETRY_DELAY=0 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "bounded retry scenario returned zero"
fi

[[ "$(grep -c '127.0.0.1.*healthz' "$command_log")" -eq 6 ]] \
  || fail "health retry override exceeded the six-attempt runtime cap"

printf 'PASS: layered monitoring retry count is capped\n'

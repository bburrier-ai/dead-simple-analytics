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
if [[ "${BACKGROUND_DESCENDANT:-}" == 1 ]]; then
  if [[ -n "${DSA_WATCHDOG_EVIDENCE_FD:-}${DSA_WATCHDOG_EVIDENCE_PATH:-}" ]]; then
    : >"$BACKGROUND_EVIDENCE_CAPABILITY_MARKER"
  fi
  (
    sleep 0.2
    if [[ -n "${DSA_WATCHDOG_EVIDENCE_FD:-}" ]]; then
      printf '%s\n' 'late descendant evidence' >&"$DSA_WATCHDOG_EVIDENCE_FD" || true
    elif [[ -n "${DSA_WATCHDOG_EVIDENCE_PATH:-}" ]]; then
      printf '%s\n' 'late descendant evidence' >>"$DSA_WATCHDOG_EVIDENCE_PATH" || true
    fi
    sleep 30
  ) &
  printf '%s\n' "$!" >"$BACKGROUND_PID_FILE"
fi
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
cat >"$TMP_DIR/state_race_test.py" <<'EOF'
import importlib.util
import os
import sys

helper_path, watchdog, parent, moved, attacker, marker, swap_name = sys.argv[1:]
spec = importlib.util.spec_from_file_location("watchdog_state", helper_path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load watchdog state helper")
watchdog_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watchdog_state)
open_private_file = watchdog_state.open_private_file


def swap_ancestor_before_open(directory_fd, name, flags):
    if name == swap_name and not os.path.exists(marker):
        os.rename(parent, moved)
        os.symlink(attacker, parent, target_is_directory=True)
        open(marker, "w").close()
    return open_private_file(directory_fd, name, flags)


watchdog_state.open_private_file = swap_ancestor_before_open
raise SystemExit(
    watchdog_state.run_watchdog(
        os.path.join(parent, "subdir"),
        ["/bin/bash", watchdog],
    )
)
EOF
cat >"$TMP_DIR/hold_lock.py" <<'EOF'
import fcntl
import os
import sys
import time

lock_path, marker = sys.argv[1:]
fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
open(marker, "w").close()
time.sleep(10)
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

python3 - <<'PY' >"$TMP_DIR/state/failures.log"
print("x" * (300 * 1024))
PY
: >"$output_file"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  FAIL_STEP=dns \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "byte-bounded failure log scenario returned zero"
fi

[[ "$(stat -c '%s' "$TMP_DIR/state/failures.log")" -le 262144 ]] \
  || fail "failure evidence log exceeded 256 KiB"
grep -q 'DSA watchdog failed at .*Z: dns' "$TMP_DIR/state/failures.log" \
  || fail "byte-bounded failure log dropped newest evidence"

printf 'PASS: persistent failure evidence has a practical byte bound\n'

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

grep -q 'state directory path contains a symbolic link or non-directory' "$output_file" \
  || fail "symlinked state directory failure is not actionable"
[[ ! -e "$TMP_DIR/attacker-state/failures.log" ]] \
  || fail "watchdog wrote failure evidence through a state-directory symlink"

printf 'PASS: symlinked state directory is rejected\n'

rm -rf "$TMP_DIR/state-parent" "$TMP_DIR/attacker-parent"
mkdir "$TMP_DIR/attacker-parent"
ln -s "$TMP_DIR/attacker-parent" "$TMP_DIR/state-parent"
: >"$output_file"
if PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state-parent/subdir" \
  APP_DOMAIN=stats.example.test \
  FAIL_STEP=dns \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "state directory beneath a symlinked parent was accepted"
fi

grep -q 'state directory path contains a symbolic link' "$output_file" \
  || fail "symlinked state-directory parent failure is not actionable"
[[ ! -e "$TMP_DIR/attacker-parent/subdir/failures.log" ]] \
  || fail "watchdog wrote failure evidence through a state-directory parent symlink"
[[ ! -e "$TMP_DIR/attacker-parent/subdir/watchdog.lock" ]] \
  || fail "watchdog opened its lock through a state-directory parent symlink"

printf 'PASS: symlinked state directory parent is rejected before evidence or lock writes\n'

rm -rf "$TMP_DIR/state"
mkdir -m 700 "$TMP_DIR/state"
mkfifo -m 600 "$TMP_DIR/state/watchdog.lock"
: >"$output_file"
if /usr/bin/timeout 2 env \
  PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "FIFO watchdog lock was accepted"
else
  fifo_status=$?
fi
[[ "$fifo_status" -ne 124 ]] || fail "FIFO watchdog lock blocked the watchdog"
grep -q 'watchdog state file is not a private owned file: watchdog.lock' "$output_file" \
  || fail "FIFO watchdog lock failure is not actionable"

printf 'PASS: FIFO watchdog lock is rejected without blocking\n'

for swap_name in watchdog.lock failures.log; do
  race_slug="${swap_name//./-}"
  race_root="$TMP_DIR/state-race-$race_slug"
  rm -rf "$race_root"
  mkdir -p "$race_root/parent/subdir" "$race_root/attacker/subdir"
  : >"$output_file"
  PATH="$TMP_DIR/bin:$PATH" \
    COMMAND_LOG="$command_log" \
    LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    REPO_DIR="$TMP_DIR/repo" \
    APP_DOMAIN=stats.example.test \
    FAIL_STEP=dns \
    HEALTH_RETRIES=1 \
    python3 "$TMP_DIR/state_race_test.py" \
      "$SCRIPT_DIR/watchdog_state.py" \
      "$WATCHDOG" \
      "$race_root/parent" \
      "$race_root/moved" \
      "$race_root/attacker" \
      "$race_root/swapped" \
      "$swap_name" \
      >"$output_file" 2>&1 || true

  [[ -e "$race_root/swapped" ]] \
    || fail "ancestor swap regression did not exercise the $swap_name race window"
  [[ ! -e "$race_root/attacker/subdir/failures.log" ]] \
    || fail "$swap_name ancestor swap redirected failure evidence into attacker storage"
  [[ ! -e "$race_root/attacker/subdir/watchdog.lock" ]] \
    || fail "$swap_name ancestor swap redirected the watchdog lock into attacker storage"
  [[ -e "$race_root/moved/subdir/failures.log" ]] \
    || fail "$swap_name ancestor swap did not persist evidence through the anchored directory fd"
  [[ -e "$race_root/moved/subdir/watchdog.lock" ]] \
    || fail "$swap_name ancestor swap did not open the lock through the anchored directory fd"
done

printf 'PASS: lock and failure-evidence ancestor swaps cannot redirect state writes\n'

rm -rf "$TMP_DIR/state"
: >"$output_file"
: >"$command_log"
if /usr/bin/timeout 2 env \
  PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  FAIL_STEP=dns \
  BACKGROUND_DESCENDANT=1 \
  BACKGROUND_EVIDENCE_CAPABILITY_MARKER="$TMP_DIR/background-evidence-capability" \
  BACKGROUND_PID_FILE="$TMP_DIR/background-descendant.pid" \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "background-descendant failure returned zero"
else
  descendant_status=$?
fi
[[ "$descendant_status" -ne 124 ]] \
  || fail "background descendant held evidence transport open and hung the watchdog"
[[ ! -e "$TMP_DIR/background-evidence-capability" ]] \
  || fail "watchdog exposed its evidence transport capability to a descendant"
grep -q 'dns lookup failed' "$TMP_DIR/state/failures.log" \
  || fail "background-descendant failure evidence was not persisted"

: >"$output_file"
: >"$command_log"
if ! PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  fail "watchdog lock remained held by a background descendant"
fi
[[ ! -s "$output_file" ]] || fail "healthy run after background descendant produced output"
sleep 0.3
! grep -q 'late descendant evidence' "$TMP_DIR/state/failures.log" \
  || fail "late background-descendant write escaped into persistent evidence"
kill "$(<"$TMP_DIR/background-descendant.pid")" 2>/dev/null || true

printf 'PASS: background descendants cannot hang evidence capture or retain the lock\n'

lock_marker="$TMP_DIR/lock-held"
python3 "$TMP_DIR/hold_lock.py" "$TMP_DIR/state/watchdog.lock" "$lock_marker" &
lock_holder_pid=$!
for _ in {1..100}; do
  [[ -e "$lock_marker" ]] && break
  sleep 0.01
done
[[ -e "$lock_marker" ]] || fail "lock contention test did not acquire the lock"
: >"$output_file"
: >"$command_log"
if ! PATH="$TMP_DIR/bin:$PATH" \
  COMMAND_LOG="$command_log" \
  LOCAL_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REMOTE_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  REPO_DIR="$TMP_DIR/repo" \
  STATE_DIR="$TMP_DIR/state" \
  APP_DOMAIN=stats.example.test \
  HEALTH_RETRIES=1 \
  bash "$WATCHDOG" >"$output_file" 2>&1; then
  kill "$lock_holder_pid" 2>/dev/null || true
  fail "contended watchdog returned nonzero"
fi
kill "$lock_holder_pid" 2>/dev/null || true
wait "$lock_holder_pid" 2>/dev/null || true
[[ ! -s "$output_file" ]] || fail "contended watchdog produced output"
[[ ! -s "$command_log" ]] || fail "contended watchdog ran deployment or health commands"

printf 'PASS: lock contention exits silently without running watchdog work\n'

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

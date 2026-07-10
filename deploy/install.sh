#!/usr/bin/env bash
# Dead Simple Analytics - production install (non-root friendly).
# Intended for a deploy user with docker group + passwordless caddy reload.
set -euo pipefail

DOMAIN=""
USERNAME="admin"
FORCE_ENV=0
CADDY_SITES_DIR="${CADDY_SITES_DIR:-/etc/caddy/sites}"
REPO="${DSA_REPO:-https://github.com/bburrier-ai/dead-simple-analytics.git}"
COMPONENTS_REPO="${COMPONENTS_REPO:-https://github.com/bburrier-ai/components.git}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  echo "Usage: install.sh --domain stats.example.com [--username admin] [--force-env]"
  echo ""
  echo "Run from a clone (e.g. /opt/apps/dead-simple-analytics), or set DSA_INSTALL_DIR."
  echo "Expects Docker available to the current user and Caddy site drop-ins in ${CADDY_SITES_DIR}."
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --username) USERNAME="$2"; shift 2 ;;
    --force-env) FORCE_ENV=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

[[ -n "$DOMAIN" ]] || usage

if [[ "${EUID:-0}" -eq 0 ]]; then
  echo "Do not run install.sh as root. Use the deploy user (docker group + caddy sudo)."
  exit 1
fi

if ! command -v docker >/dev/null; then
  echo "docker not found. Install Docker and add this user to the docker group first."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Cannot talk to Docker. Is this user in the docker group? Try a new login session."
  exit 1
fi

rand() { openssl rand -hex 24; }

INSTALL_DIR="${DSA_INSTALL_DIR:-}"
if [[ -z "$INSTALL_DIR" ]]; then
  if [[ -f "${REPO_ROOT}/docker-compose.yml" ]]; then
    INSTALL_DIR="$REPO_ROOT"
  else
    INSTALL_DIR="/opt/apps/dead-simple-analytics"
  fi
fi
APPS_DIR="$(dirname "$INSTALL_DIR")"
COMPONENTS_DIR="${DSA_COMPONENTS_DIR:-${APPS_DIR}/components}"

echo "==> Install dir: ${INSTALL_DIR}"
echo "==> Components:  ${COMPONENTS_DIR}"

echo "==> Ensuring repositories"
mkdir -p "$APPS_DIR"
if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  git clone --depth 1 "$REPO" "$INSTALL_DIR"
fi
if [[ ! -d "${COMPONENTS_DIR}/.git" ]]; then
  git clone --depth 1 "$COMPONENTS_REPO" "$COMPONENTS_DIR"
fi
if [[ ! -d "${COMPONENTS_DIR}/public" ]]; then
  echo "Missing ${COMPONENTS_DIR}/public - components repo looks incomplete."
  exit 1
fi

cd "$INSTALL_DIR"

if [[ -f .env && "$FORCE_ENV" -ne 1 ]]; then
  echo "==> Keeping existing .env (pass --force-env to regenerate)"
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
  ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
else
  echo "==> Writing .env"
  ADMIN_PASSWORD="$(rand)"
  PG_PASS="$(rand)"
  cat > .env <<EOF
POSTGRES_USER=dsa
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=dead_simple_analytics
DATABASE_URL=postgresql+psycopg://dsa:${PG_PASS}@postgres:5432/dead_simple_analytics
DSA_HOST_PORT=8082
ADMIN_USERNAME=${USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
JWT_SECRET=$(rand)
JWT_EXPIRE_MINUTES=1440
SESSION_COOKIE_NAME=session
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
IP_HASH_SALT=$(rand)
COLLECT_RATE_LIMIT_PER_MIN=120
PUBLIC_BASE_URL=https://${DOMAIN}
COMPONENTS_CDN_URL=/components
GEOLITE2_DB_PATH=
APP_ENV=production
CORS_ORIGINS=https://${DOMAIN}
LOG_LEVEL=INFO
EOF
fi

echo "==> Starting DSA (docker compose)"
docker compose up -d --build

echo "==> Configuring Caddy site ${DOMAIN}"
if [[ ! -d "$CADDY_SITES_DIR" ]]; then
  echo "Missing ${CADDY_SITES_DIR}."
  echo "Create it (owned by deploy) and ensure /etc/caddy/Caddyfile has: import sites/*"
  exit 1
fi
if [[ ! -w "$CADDY_SITES_DIR" ]]; then
  echo "${CADDY_SITES_DIR} is not writable by $(whoami)."
  exit 1
fi

SITE_FILE="${CADDY_SITES_DIR}/${DOMAIN}.caddy"
cat > "$SITE_FILE" <<EOF
${DOMAIN} {
    reverse_proxy localhost:8082 {
        flush_interval -1
    }
}
EOF

if command -v sudo >/dev/null; then
  sudo systemctl reload caddy || sudo systemctl restart caddy
else
  echo "sudo not available - reload caddy manually after install."
fi

echo ""
echo "DSA is ready (once DNS propagates):"
echo "  Login:    https://${DOMAIN}/login"
echo "  Username: ${USERNAME}"
if [[ -n "${ADMIN_PASSWORD}" ]]; then
  echo "  Password: ${ADMIN_PASSWORD}"
  echo ""
  echo "Save the password - it is only shown when .env is created."
else
  echo "  Password: (see existing .env ADMIN_PASSWORD)"
fi
echo "  Snippet:  https://${DOMAIN}/dsa.js"
echo "  App dir:  ${INSTALL_DIR}"
echo ""

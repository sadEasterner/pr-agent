#!/usr/bin/env bash
# Immutable production deploy. Copy to /usr/local/bin/pr-manager-deploy and
# keep that copy root-owned. GitHub Actions may only invoke this path.
set -euo pipefail
umask 077

APP_DIR="/root/hosein/pr-manager"
COMPOSE_FILE="docker-compose.prod.yml"
PROJECT="pr-manager"
ALLOWED_BRANCH="main"
LOCK_FILE="/var/lock/pr-manager-deploy.lock"
HEALTH_API="http://127.0.0.1:8110/health"
HEALTH_DASH="http://127.0.0.1:8111/healthz"
REMOTE_RE="github.com([:/]|-pr-manager:)sadEasterner/pr-mangement(\.git)?$"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*"; exit 1; }

if [[ "$(id -u)" -ne 0 ]]; then
  die "must run as root"
fi

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  die "another deploy is running"
fi

[[ -d "${APP_DIR}" ]] || die "missing ${APP_DIR}"
cd "${APP_DIR}"
[[ -d .git ]] || die "${APP_DIR} is not a git checkout"
[[ -f .env ]] || die "missing ${APP_DIR}/.env (secrets must stay on the server)"
chmod 600 .env
[[ -f "${COMPOSE_FILE}" ]] || die "missing ${COMPOSE_FILE}"

remote_url="$(git remote get-url origin)"
[[ "${remote_url}" =~ ${REMOTE_RE} ]] || die "unexpected origin: ${remote_url}"

previous_sha="$(git rev-parse HEAD)"
log "fetching origin/${ALLOWED_BRANCH} from ${previous_sha}"
git fetch --prune --no-tags --depth=50 origin "${ALLOWED_BRANCH}"
git checkout -B "${ALLOWED_BRANCH}" "origin/${ALLOWED_BRANCH}"
git reset --hard "origin/${ALLOWED_BRANCH}"
new_sha="$(git rev-parse HEAD)"
branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "${branch}" == "${ALLOWED_BRANCH}" ]] || die "not on ${ALLOWED_BRANCH} (${branch})"
[[ -f .env ]] || die ".env disappeared after git reset"

export COMPOSE_PROJECT_NAME="${PROJECT}"
export DOCKER_BUILDKIT=1
export COMPOSE_PARALLEL_LIMIT=1

log "building api"
docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" build api
log "building dashboard"
docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" build dashboard
log "starting stack"
docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" up -d --remove-orphans --no-build

healthy=""
for _ in $(seq 1 24); do
  api_ok="$(curl -fsS -m 5 "${HEALTH_API}" 2>/dev/null || true)"
  dash_code="$(curl -fsS -m 5 -o /dev/null -w '%{http_code}' "${HEALTH_DASH}" 2>/dev/null || echo 000)"
  if [[ "${api_ok}" == *'"status":"ok"'* && "${dash_code}" == "200" ]]; then
    healthy="yes"
    break
  fi
  sleep 5
done

if [[ -z "${healthy}" ]]; then
  log "health check failed; rolling back to ${previous_sha}"
  git reset --hard "${previous_sha}"
  docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" build api
  docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" build dashboard
  docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" up -d --remove-orphans --no-build
  die "deploy of ${new_sha} failed health checks"
fi

log "deployed ${new_sha}"
docker compose -f "${COMPOSE_FILE}" --project-name "${PROJECT}" ps

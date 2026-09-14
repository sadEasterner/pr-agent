# Deploy PR Manager

This is the production guide. For Git host wiring, see [PROVIDERS.md](PROVIDERS.md).

## What you are deploying

Three containers (or equivalent services):

| Service | Role | Default publish |
| --- | --- | --- |
| `postgres` | Review history | internal only |
| `api` | Webhooks, rules, AI, admin API | `127.0.0.1:8000` locally; bind to localhost in production |
| `dashboard` | React UI; proxies `/api` to the API | public HTTP/HTTPS |

The API must not be reachable from the internet except through TLS and your reverse proxy. Webhooks hit the API. Humans use the dashboard.

## 1. Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A Git host you control (Gitea, Forgejo, GitHub, GitHub Enterprise, GitLab, or GitLab self-managed)
- A bot token that can **read pull requests and post comments**, not merge
- TLS in front of the public URL (Caddy, nginx, Traefik, or a cloud load balancer)
- 1 vCPU / 2 GB RAM is enough for a small team

## 2. Copy and lock secrets

```bash
cp .env.example .env
chmod 600 .env
```

Never commit `.env`. Never bake tokens into the image.

Minimum production values:

```text
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@postgres:5432/prmanager

SCM_PROVIDER=gitea
SCM_BASE_URL=https://git.example.com
SCM_TOKEN=...
SCM_WEBHOOK_SECRET=...          # long random string, 32+ bytes

AI_ENABLED=true
AI_PROVIDER=deepseek
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=...

ADMIN_USERNAME=...
ADMIN_PASSWORD=...
AUTH_SESSION_SECRET=...         # long random string
AUTH_COOKIE_SECURE=true         # true when the dashboard is served over HTTPS

CORS_ORIGINS=https://pr-manager.example.com
```

Generate secrets:

```bash
openssl rand -hex 32
```

Use one value for `SCM_WEBHOOK_SECRET` and the webhook secret on the Git host. Use a different value for `AUTH_SESSION_SECRET`.

If the dashboard is HTTP-only (IP:port on a private network), keep `AUTH_COOKIE_SECURE=false`.

## 3. Start the stack

From the repository root:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

For a first local check, `docker compose up --build` is enough. Production should use `docker-compose.prod.yml` so the API listens on `127.0.0.1` only.

Confirm:

```bash
curl -fsS http://127.0.0.1:8110/health
curl -fsS http://127.0.0.1:8110/ready
```

`/health` is liveness. `/ready` checks the database and required Git-host config. AI is not required for readiness.

The API container runs `alembic upgrade head` before uvicorn. A failed migration stops the container.

## 4. Put TLS in front

Point HTTPS at:

- Dashboard (humans): the dashboard container, e.g. port 8111
- API (webhooks): `https://your.domain/pr-manager-api/` → `127.0.0.1:8110`

Forward these headers through the proxy (see `docker/nginx/pr-manager.hosein.work.conf`):

- `X-Gitea-Event`, `X-Gitea-Signature`
- `X-Hub-Signature-256`
- `X-GitHub-Event`
- `X-Gitlab-Event`, `X-Gitlab-Token`

Then create the webhook using the URLs in [PROVIDERS.md](PROVIDERS.md).

## 5. Open the product

1. Open the dashboard. Overview, PRs, and findings are public.
2. Open `/admin`, sign in, and confirm **AI review API** and **PR comments**.
3. Open a small test PR on the Git host.
4. Confirm a `PR-MANAGER-REVIEW` comment appears (if comments are on).
5. Confirm the dashboard shows the same review.

If the webhook returns 401, the signature or GitLab token does not match `SCM_WEBHOOK_SECRET`.

If the dashboard shows a review but Gitea/GitHub/GitLab does not, PR comments are off on the admin page.

## 6. Operations

- **Logs:** `docker compose -f docker-compose.prod.yml logs -f api`
- **Restart after rule changes:** rebuild/restart `api` (`CONFIG_DIR=/config` is copied into the image)
- **Database:** named volume `postgres-data`. Back it up with `pg_dump`.
- **Updates:** rebuild `api` and `dashboard`. Do not recreate Postgres unless you intend to wipe history.
- **Admin toggles** survive container rebuilds; they live in Postgres.

## 7. What not to do

- Do not give the bot token merge, protect-branch bypass, or owner rights
- Do not expose Postgres or the API port on `0.0.0.0`
- Do not set `APP_ENV=production` without admin credentials and a webhook secret
- Do not put `.env` in git, CI artifacts, or image layers
- Do not allow the AI to approve or merge; the policy engine forbids it

## 8. Publish checklist

Before you share this as a product:

- [ ] `SCM_PROVIDER` documented for your audience
- [ ] `.env.example` has empty secrets
- [ ] Production compose binds the API to localhost
- [ ] TLS terminates in front of dashboard and webhooks
- [ ] A test PR was reviewed end to end
- [ ] Admin login works on `/admin` only
- [ ] `pnpm nx test api` and `pnpm nx test dashboard` pass
- [ ] Backup plan for the Postgres volume exists

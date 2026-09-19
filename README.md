# PR Manager

AI-assisted pull request review for **Gitea, GitHub, GitLab, and Forgejo**.

The AI is a reviewer. **It never merges, approves, closes, or pushes code.** Humans keep merge authority on the Git host.

## What you get

- Webhooks from your Git host, verified with HMAC or a GitLab token
- Deterministic rules (size, dangerous paths, workspace isolation, labels)
- Optional AI review (DeepSeek, OpenAI, or any OpenAI-compatible endpoint)
- A dashboard for history, findings, and trends
- An admin page to turn the AI API and PR comments on or off

```text
   Gitea / GitHub / GitLab
            |
         webhooks
            v
     FastAPI PR Manager
        |      |      |
     Rules    AI   PostgreSQL
        |      |
        +------+
            |
     comment on the PR
            |
      React dashboard
```

## Docs

| Guide | When to read it |
| --- | --- |
| [docs/PROVIDERS.md](docs/PROVIDERS.md) | Connect Gitea, GitHub, or GitLab |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Docker, production, secrets, TLS, reverse proxy |
| [docs/ADDING-A-PROVIDER.md](docs/ADDING-A-PROVIDER.md) | Add Bitbucket or another host |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Local setup and pull requests |
| [SECURITY.md](SECURITY.md) | Vulnerability reports |

This project is licensed under the [MIT License](LICENSE).

## Quick start (local)

```bash
cp .env.example .env
# set SCM_PROVIDER, SCM_BASE_URL, SCM_TOKEN, SCM_WEBHOOK_SECRET
pnpm install
uv sync --project apps/api --all-extras
docker compose up -d postgres
pnpm nx run api:migrate
pnpm nx serve api
pnpm nx serve dashboard
```

Compose publishes PostgreSQL on host port **15432**. Point a local API at:

```text
DATABASE_URL=postgresql+asyncpg://prmanager:prmanager@localhost:15432/prmanager
```

API: http://localhost:8000  
Dashboard: http://localhost:5173  
API docs: http://localhost:8000/docs

## Docker (all-in-one)

```bash
cp .env.example .env
docker compose up --build
```

Dashboard: http://localhost:8088  
API: http://localhost:8000

The API runs Alembic migrations on startup. Secrets come from `.env`, never from the image.

## Git host in one screen

```text
SCM_PROVIDER=gitea          # or github, gitlab
SCM_BASE_URL=https://git.example.com
SCM_TOKEN=...               # read PRs, post comments, add labels — not merge
SCM_WEBHOOK_SECRET=...
```

| Provider | Webhook URL | Auth |
| --- | --- | --- |
| Gitea / Forgejo | `POST /webhooks/gitea` | `X-Gitea-Signature` / `X-Hub-Signature-256` |
| GitHub | `POST /webhooks/github` | `X-Hub-Signature-256` |
| GitLab | `POST /webhooks/gitlab` | `X-Gitlab-Token` |
| Configured host | `POST /webhooks/scm` | Same as `SCM_PROVIDER` |

Legacy `GITEA_*` variables still work if `SCM_*` is empty.

Token scopes must **not** be used to merge, approve, close, or push. Those actions are forbidden in `config/review-rules.yaml` even if the token could do them.

## Monorepo

```text
.
├── apps/api            FastAPI + SQLAlchemy + Alembic (uv)
├── apps/dashboard      React + Vite + Tailwind (pnpm)
├── packages/           Shared UI and TypeScript types
├── config/             Review rules
├── docs/
└── docker-compose.yml
```

Nx orchestrates both ecosystems. It does not replace uv or pnpm.

```bash
pnpm nx serve api
pnpm nx serve dashboard
pnpm nx test api
pnpm nx test dashboard
pnpm nx run-many -t lint
```

## AI

```text
AI_ENABLED=true
AI_PROVIDER=deepseek          # or openai
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=...          # or OPENAI_API_KEY
```

If `AI_ENABLED=false`, rules still run. Admins can also disable AI and PR comments at runtime from `/admin` without restarting.

## Admin page

Only `/admin` is login-protected. Overview and PR pages stay public.

Set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `AUTH_SESSION_SECRET` in `.env`. Production refuses to start without them.

## Security

- Webhook signatures are required
- AI never gets merge authority
- Diff size, file count, and generated/vendor paths are limited
- Logs redact tokens, passwords, and webhook secrets
- Request bodies have a size cap

See [docs/DEPLOY.md](docs/DEPLOY.md) before you publish a deployment.

CI on GitHub Actions and Gitea Actions runs lint, tests, and the dashboard build. It does not deploy.


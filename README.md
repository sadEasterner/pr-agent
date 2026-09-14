# Gitea PR Manager

Internal Pull Request management and AI code-review platform for a self-hosted Gitea instance.

The AI is a reviewer and recommendation engine. **It never merges, approves, closes, or pushes code.** Merge authority stays with humans in Gitea.

## 1. Architecture

```text
                SELF-HOSTED GITEA
                       |
                       | webhooks
                       v
             +--------------------+
             | FastAPI PR Manager |
             +--------------------+
                |       |       |
                v       v       v
             Rules     AI    PostgreSQL
             Engine  Reviewer    |
                |                 |
                +--------+--------+
                         |
                         v
                       Gitea
                         +
                         |
                         v
                 React Dashboard
                         |
                         v
                    FastAPI API
```

Separated responsibilities:

1. Deterministic PR automation (labels, size, dangerous paths, reviewers)
2. AI code review (advisory, structured, SHA-scoped)
3. Human approval and merge control
4. Persistent review history
5. Engineering analytics
6. Dashboard and reporting

Webhook requests are acknowledged immediately. Review work runs on an in-process job queue that can later be replaced with Redis/ARQ/Celery without changing PR management logic.

## 2. Monorepo layout

```text
.
├── apps/
│   ├── api/                 FastAPI + SQLAlchemy + Alembic (uv)
│   └── dashboard/           React + Vite + Tailwind (pnpm)
├── packages/
│   ├── ui/                  Shared dashboard components
│   └── shared-types/        Shared TypeScript API types
├── config/
│   ├── review-rules.yaml    Global PR, AI, and automation policy
│   └── repositories/        Per-repository engineering rules
├── docker/
├── nx.json
├── pnpm-workspace.yaml
└── docker-compose.yml
```

Nx orchestrates both ecosystems. It does not replace uv or pnpm.

## 3. Nx

Useful targets:

```bash
pnpm nx serve api
pnpm nx test api
pnpm nx lint api
pnpm nx typecheck api

pnpm nx serve dashboard
pnpm nx test dashboard
pnpm nx lint dashboard
pnpm nx typecheck dashboard
pnpm nx build dashboard

pnpm nx run-many -t test
pnpm nx run-many -t lint
pnpm nx affected -t test
```

Python targets execute uv:

```bash
uv run pytest
uv run ruff check .
uv run mypy app
uv run uvicorn app.main:app
```

## 4. pnpm

JavaScript and TypeScript dependencies are managed with pnpm workspaces.

```bash
pnpm install
```

Do not install Python packages with npm.

## 5. uv

Python 3.12+ dependencies are managed with uv in `apps/api`.

```bash
uv sync --project apps/api --all-extras
```

## 6. Local development

```bash
cp .env.example .env
pnpm install
uv sync --project apps/api --all-extras
docker compose up -d postgres
pnpm nx run api:migrate
pnpm nx serve api
pnpm nx serve dashboard
```

Compose publishes PostgreSQL on host port **15432** so it does not collide with a local Postgres on 5432. The API container still uses `postgres:5432` internally. For a local API talking to Compose Postgres:

```text
DATABASE_URL=postgresql+asyncpg://prmanager:prmanager@localhost:15432/prmanager
```

API: http://localhost:8000  
Dashboard: http://localhost:5173  
API docs: http://localhost:8000/docs

## 7. Environment variables

See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL (`postgresql+asyncpg://...`) |
| `GITEA_BASE_URL` | Self-hosted Gitea origin |
| `GITEA_TOKEN` | Gitea API token |
| `GITEA_WEBHOOK_SECRET` | Shared webhook HMAC secret |
| `AI_ENABLED` | Enable the AI reviewer |
| `AI_PROVIDER` | `openai` or an OpenAI-compatible provider |
| `AI_MODEL` | Model name |
| `OPENAI_API_KEY` | Provider API key |
| `OPENAI_BASE_URL` | Override for compatible endpoints, including Ollama gateways |
| `CORS_ORIGINS` | Dashboard origins |

Secrets are read from the environment. They are never baked into images and never written to logs.

## 8. PostgreSQL

Production uses PostgreSQL 16. Schema is managed with Alembic:

```bash
pnpm nx run api:migrate
# or
uv run --project apps/api alembic upgrade head
```

Tests may use SQLite through the same SQLAlchemy models. Do not use SQLite in production.

## 9. Gitea token configuration

Create a Gitea user or application token that can:

- Read pull requests, diffs, commits, and repository metadata
- Post and update issue comments
- Add labels
- Request reviewers, if your Gitea version supports it

The token must **not** be used to merge, approve, close, or push. Those actions are forbidden in `config/review-rules.yaml` even if the token happens to allow them.

```text
GITEA_BASE_URL=https://gitea.example.com
GITEA_TOKEN=...
```

## 10. Gitea webhook setup

In each repository (or a Gitea organization hook):

1. URL: `https://pr-manager.example.com/webhooks/gitea`
2. HTTP method: POST
3. Secret: the same value as `GITEA_WEBHOOK_SECRET`
4. Events: Pull Request (`opened`, `reopened`, `synchronized`, `edited`, `closed`)

The API verifies `X-Gitea-Signature` / `X-Hub-Signature-256`. Invalid signatures are rejected. Duplicate deliveries for the same repository, PR number, event type, and head SHA are ignored.

## 11. OpenAI configuration

```text
AI_ENABLED=true
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
```

The application is not coupled to OpenAI. Add another provider under `apps/api/app/ai/providers/` and select it with `AI_PROVIDER`. Compatible endpoints (including internal gateways or Ollama proxies) can use `OPENAI_BASE_URL`.

If `AI_ENABLED=false`, deterministic rules still run and a human-review recommendation is stored.

## 12. Review rules

Global rules live in `config/review-rules.yaml`:

- Missing descriptions and large PRs
- Dangerous, migration, infrastructure, and test paths
- Labels and suggested reviewers
- AI checks, ignores, and `minimum_confidence`
- Path-specific AI checks
- Project engineering rules
- Automation allow/deny lists

Deterministic rules never call the model. The AI reviewer never replaces them.

## 13. Repository-specific rules

Add YAML files in `config/repositories/` named `{owner}__{repo}.yaml`.

Example: `config/repositories/acme__payments.yaml`

```yaml
project_rules:
  - "Payment amounts must be stored as integers in the smallest currency unit."
  - "All payment mutations must be idempotent."
```

Repository rules are combined with global rules, path rules, PR metadata, and the filtered diff.

## 14. Running tests

```bash
pnpm nx test api
pnpm nx test dashboard
pnpm nx run-many -t lint
pnpm nx run-many -t typecheck
pnpm nx build dashboard
```

Backend tests mock Gitea and the AI provider. They do not need internet access, a live Gitea, or OpenAI.

## 15. Docker deployment

```bash
cp .env.example .env
docker compose up --build
```

The stack includes `api`, `dashboard`, and `postgres`.

- Containers run as non-root users
- PostgreSQL data is persisted in a named volume
- Healthchecks and restart policies are enabled
- Secrets come from environment variables
- The API runs Alembic migrations on startup

Dashboard: http://localhost:8088  
API: http://localhost:8000

## 16. Dashboard

Professional React dashboard with:

- Overview cards and process charts
- Pull request list with filters
- PR detail, findings by severity, and review history by SHA
- Findings, repositories, trends, and settings

The UI makes it obvious that AI output is a recommendation. Merge stays in Gitea via the “Open in Gitea” link. The dashboard does not merge pull requests.

## 17. Analytics

```text
GET /api/analytics/summary
GET /api/analytics/trends
GET /api/analytics/findings
GET /api/analytics/repositories
GET /api/analytics/prs
GET /api/analytics/prs/{repository}/{number}
```

Metrics focus on engineering patterns: PR size, time to first review, time to merge, severity, categories, repeated modules, and review iterations. There is no developer score.

## 18. Security model

- HMAC webhook verification
- Strict Pydantic validation
- HTTP body size limits and request timeouts
- AI diff size, file count, and chunk limits
- Binary, generated, vendor, `node_modules`, and lockfile exclusion
- Structured logs with secret redaction
- Environment-based secrets
- No shell execution and no evaluation of repository commands
- Repository content is treated as hostile input

## 19. AI permission model

`config/review-rules.yaml` separates recommendations from permissions.

Allowed in v1:

- Read PRs and diffs
- Post one summary review
- Add labels
- Recommend merge in language only
- Request human review

Forbidden, always:

- `merge_pr`
- `approve_pr`
- `close_pr`
- `push_code`
- `modify_repository`

If the model says “approved” or “ready to merge”, the system stores `ready_for_human_review` / `waiting_for_human`. The Gitea comment states that human approval is required. Allowed recommendation values are:

- `ready_for_human_review`
- `changes_requested`
- `high_risk`
- `unable_to_review`

The same commit SHA is never reviewed twice unless a human explicitly requests a re-review.

## 20. Production deployment

1. Provision PostgreSQL and set `DATABASE_URL`.
2. Set Gitea URL, token, and webhook secret from a secret manager.
3. Keep `AI_ENABLED` and the provider key in secrets. Do not put them in the image.
4. Deploy `api` and `dashboard` behind TLS.
5. Point Gitea webhooks at `https://<api-host>/webhooks/gitea`.
6. Confirm `GET /health` and `GET /ready`.
7. `/health` does not require the AI provider. `/ready` checks configuration and the database.
8. Start with `automation.mode: review_only` and the default forbidden merge/approve actions.
9. Tune `config/review-rules.yaml` per team, then add repository files as needed.

Dashboard-based approvals can be added later. They are intentionally omitted from v1 because merge is a security-sensitive action.

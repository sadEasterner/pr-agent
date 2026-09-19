# Contributing

## Development

```bash
cp .env.example .env
pnpm install
uv sync --project apps/api --all-extras
docker compose up -d postgres
pnpm nx run api:migrate
pnpm nx serve api
pnpm nx serve dashboard
```

## Checks

```bash
pnpm nx run api:lint
pnpm nx run api:test
pnpm nx run dashboard:lint
pnpm nx run dashboard:typecheck
pnpm nx run dashboard:test
pnpm nx run dashboard:build
```

## Rules

- Do not add merge, approve, close, or push calls to a Git host adapter.
- Do not commit secrets, production hostnames, or personal deploy scripts.
- Keep Git comments short and factual.
- Prefer tests over screenshots when you change behavior.

# Add a Git host provider

The review job, rules engine, AI reviewer, and dashboard are host-agnostic. To support another Git host (Bitbucket, Azure DevOps, Gerrit, …) add an adapter under `apps/api/app/scm/` and leave the rest of the app alone.

## Contract

Implement `ScmProvider` in `app/scm/base.py`:

1. `fetch_snapshot(repository, number)` — PR metadata, file list, unified diff, commit count
2. `post_or_update_review_comment(...)` — upsert one comment that contains `PR-MANAGER-REVIEW`
3. `add_labels(...)` — best-effort; must not merge
4. `close()` — close the HTTP client

Return `PullRequestSnapshot` and `FileChange` from `app/scm/models.py`. Never return host-specific types into the processor.

## Webhooks

1. Parse the vendor payload into `PullRequestEvent` (`app/scm/events.py`).
2. Verify the signature in `app/webhooks/security.py` (HMAC, token header, or both).
3. Register the name in `SUPPORTED_PROVIDERS` and `create_scm_provider()`.
4. Document the webhook URL and token scopes in `docs/PROVIDERS.md`.

Ignore closed and merged events. Map “push to the PR branch” to action `synchronized`.

## What you must not implement

Do not add merge, approve, close, or push methods to the provider. Policy in `config/review-rules.yaml` forbids them, and the processor never calls them.

## Tests

Add HTTP mock tests next to `apps/api/tests/test_scm.py` for snapshot fetch, comment upsert, and webhook parsing. Keep Gitea tests green; they prove the processor still works through the adapter.

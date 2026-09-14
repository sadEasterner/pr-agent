# Git host providers

PR Manager talks to Git hosts through `apps/api/app/scm/`. The review pipeline never imports Gitea, GitHub, or GitLab APIs directly.

Set:

```text
SCM_PROVIDER=gitea    # github | gitlab | forgejo
SCM_BASE_URL=...
SCM_TOKEN=...
SCM_WEBHOOK_SECRET=...
```

`GITEA_BASE_URL`, `GITEA_TOKEN`, and `GITEA_WEBHOOK_SECRET` still work as fallbacks.

Webhook path: `https://<your-api>/webhooks/<provider>`  
Or `https://<your-api>/webhooks/scm` to use `SCM_PROVIDER`.

The bot token must be able to read pull/merge requests, diffs, and comments, and to post comments and labels. It must not merge, approve, close, or push.

---

## Gitea or Forgejo

```text
SCM_PROVIDER=gitea
SCM_BASE_URL=https://gitea.example.com
```

Forgejo is API-compatible. Use `gitea` (or `forgejo`) as the provider.

**Token:** a user or application token with repository read, issue/PR comment write, and label write. Do not grant merge.

**Webhook** (repository or organization):

1. URL: `https://<api>/webhooks/gitea`
2. HTTP method: POST
3. Secret: same as `SCM_WEBHOOK_SECRET`
4. Events: Pull Request (`opened`, `reopened`, `synchronized`, `edited`, `closed`)

The API checks `X-Gitea-Signature` or `X-Hub-Signature-256`.

---

## GitHub (github.com or Enterprise)

```text
SCM_PROVIDER=github
SCM_TOKEN=ghp_...          # or a fine-grained / GitHub App installation token
SCM_WEBHOOK_SECRET=...
# github.com (default):
# SCM_BASE_URL=https://api.github.com
# GitHub Enterprise Server:
# SCM_BASE_URL=https://github.example.com
```

If `SCM_BASE_URL` is your GHE origin (not `api.github.com`), the client uses `{origin}/api/v3`.

**Token permissions:**

- Fine-grained: repository contents read, pull requests read/write (comments + labels)
- Classic: `repo` is broader than needed; prefer fine-grained and omit admin/merge

**Webhook:**

1. URL: `https://<api>/webhooks/github`
2. Content type: `application/json`
3. Secret: same as `SCM_WEBHOOK_SECRET`
4. Events: **Pull requests** only
5. SSL: enable verification

The API checks `X-Hub-Signature-256` and `X-GitHub-Event: pull_request`.

`synchronize` is treated the same as Gitea `synchronized`.

---

## GitLab (gitlab.com or self-managed)

```text
SCM_PROVIDER=gitlab
SCM_BASE_URL=https://gitlab.com
# self-managed:
# SCM_BASE_URL=https://gitlab.example.com
SCM_TOKEN=glpat-...
SCM_WEBHOOK_SECRET=...
```

The client calls `{SCM_BASE_URL}/api/v4`. Project paths are `group/repo` (URL-encoded).

**Token:** a project or group access token with `read_api` and `api` limited to commenting on merge requests. Do not grant `maintainer` if you can avoid it.

**Webhook:**

1. URL: `https://<api>/webhooks/gitlab`
2. Trigger: Merge request events
3. Secret token: same as `SCM_WEBHOOK_SECRET` (GitLab sends it as `X-Gitlab-Token`)

GitLab does not HMAC the body by default. The API compares `X-Gitlab-Token` to `SCM_WEBHOOK_SECRET`.

Merge request `open` / `update` / `reopen` are reviewed. `close` and `merge` are ignored.

---

## Runtime controls

On the dashboard **Admin** page:

- **AI review API** — off: rules still run, the model is not called
- **PR comments** — off: the review is stored in PR Manager, nothing is posted to the Git host

Those switches apply to the next webhook. They are stored in Postgres.

---

## Which URL to give the Git host

If the API is reverse-proxied as `/pr-manager-api/`:

| Host | URL |
| --- | --- |
| Gitea | `https://example.com/pr-manager-api/webhooks/gitea` |
| GitHub | `https://example.com/pr-manager-api/webhooks/github` |
| GitLab | `https://example.com/pr-manager-api/webhooks/gitlab` |

The proxy must forward signature headers. See [DEPLOY.md](DEPLOY.md).

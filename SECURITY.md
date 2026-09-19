# Security

## Reporting a vulnerability

Open a private GitHub security advisory, or email the maintainer listed on the
repository. Do not file a public issue for an unpatched vulnerability.

Please include:

- Affected version or commit
- Steps to reproduce
- Impact (webhook forgery, secret leakage, privilege escalation, and so on)

## What this project will not do

PR Manager is an advisory reviewer. It must never merge, approve, close, or
push. Bot tokens used with it should not have those permissions either.

## Secrets

Never commit `.env`, tokens, webhook secrets, or SSH keys. `.env.example` is
the only environment file that belongs in git, and its secret values are empty.

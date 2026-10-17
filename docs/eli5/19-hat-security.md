# The security guide

Who this is for: you care about who can call what, where secrets live, and what an attacker sees when the system talks back.

## Your mental model

Every API request must prove itself: an API key in the `X-API-Key` header or a JWT bearer token. Users come from `AUTH_USER_*` and `AUTH_API_KEY_*` environment variables at startup — no users in code or in the database.

Roles are admin, trader, viewer and system, and admins pass every role check. Secrets flow from env vars or `.env` through `secret_manager`, masked in logs and never hardcoded.

## Read this first

1. [Security](10-security.md) — the full page: the auth journey, roles, and the secrets flow.
2. [How the system works](01-how-the-system-works.md) — where the guarded front door sits in the layers.
3. [The folder map](03-folder-map.md) — what hides inside `app/security/`.
4. [Execution](07-execution.md) — the endpoints where the trader role actually matters.
5. [The dashboard](11-dashboard.md) — the second surface you expose when you serve it.

## Your flows

- Trace one request past the guards: [security](10-security.md) — rate limits, lockout, hash or signature.
- Audit the secrets path: [security](10-security.md) — `get_secret`, `require_secret`, `mask_secret`.
- Check role checks on the money endpoints: [execution](07-execution.md).
- Review the middleware wiring: [security](10-security.md) plus the API layer in [the big picture](01-how-the-system-works.md).

## Your commands

```bash
make security      # bandit + safety scans, JSON reports
make lint          # ruff + mypy over the same code
make docs-build    # keep /docs fresh after doc changes
```

## Watch out

- `.env` holds real keys and is gitignored. Never commit it, never paste its values into an issue.
- Five failed auth attempts lock the caller out for 15 minutes. While testing, that looks like a bug.
- `make security` writes `bandit-report.json` and `safety-report.json`; safety runs with `|| true`, so vulnerable deps don't fail the target.
- `require_secret` refuses to boot in production when a secret is missing. A "won't start" box may just be an unset variable.
- The dashboard and docs are served unauthenticated by default. Don't expose their ports beyond localhost.

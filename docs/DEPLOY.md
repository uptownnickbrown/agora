# Deploying Agora to Railway

Production lives at **https://frontend-production-1bbf.up.railway.app**
(Railway project `agora`, environment `production`, workspace "Nick Brown's Projects").
Push-to-deploy last verified end-to-end: 2026-06-11.

## TL;DR — shipping a change

```sh
git push origin main
```

That's the whole deploy. All three app services are GitHub-connected to
`uptownnickbrown/agora@main`, so every push to `main` builds and deploys
api, worker, and frontend from their Dockerfiles. Database migrations run
automatically (`alembic upgrade head` is the api's pre-deploy command), so a
schema change just needs its Alembic revision committed alongside the code.

Watch it land:

```sh
railway deployment list --service frontend --json   # status + commitHash
railway logs --service api                          # live logs
```

Then sanity-check prod:

```sh
curl https://frontend-production-1bbf.up.railway.app/api/health   # {"status":"ok","env":"prod"}
open  https://frontend-production-1bbf.up.railway.app/landing/
```

A frontend-only change still rebuilds api/worker (no watch paths configured —
deliberate, to keep the pipeline simple). Rebuilds are harmless: migrations
are idempotent and the nginx proxy re-resolves the api's address per request,
so brief api restarts don't strand stale connections.

## Architecture

| Service  | Source                  | Notes |
|----------|-------------------------|-------|
| frontend | `frontend/` Dockerfile  | nginx; serves SPA + `/landing/`, proxies `/api/*` to api over private IPv6. Public domain lives here. |
| api      | `backend/` Dockerfile   | uvicorn on `[::]:8000` (`BIND_HOST=::`). Pre-deploy: `alembic upgrade head`. **No public domain** — reach it through the frontend proxy. |
| worker   | `backend/` Dockerfile   | `arq app.worker.WorkerSettings` — daily close cron + fast ticks. |
| Postgres | Railway template        | `${{Postgres.DATABASE_URL}}` referenced by api/worker. Public TCP proxy (`acela.proxy.rlwy.net:54660`) for host-side scripts. |
| Redis    | Railway template        | `${{Redis.REDIS_URL}}` referenced by api/worker. |

Private networking is **IPv6-only**: anything binding for mesh traffic must
listen on `::` (api does, via `BIND_HOST`; nginx has a `listen [::]` line and
uses Railway's `fd12::10` DNS resolver via the `DNS_RESOLVER` env).

## Manual operations

Redeploy without a new commit (e.g. after changing a variable with
`skip_deploys`):

```sh
railway redeploy --service api
```

Roll back: open the service in the Railway dashboard → Deployments → redeploy
a previous SUCCESS build. (The CLI's `redeploy` only re-runs the latest.)

Change service settings the CLI lacks flags for (root directory, pre-deploy
command, healthcheck, start command): use the MCP server — `railway mcp` is
line-oriented JSON-RPC on stdio. Two sharp edges:

- `pre_deploy_command` must be a **JSON array** (`["alembic upgrade head"]`);
  a bare string fails — sometimes silently (empty response text = failure).
- The process exits when stdin closes, so drive it from a script that keeps
  the pipe open and reads replies before exiting.

## Demo world (landing-page "jump into a course")

The demo world is ordinary data in prod Postgres — it survives redeploys.

**It rotates itself nightly**: the worker's `demo_reset` cron (05:30 UTC,
right after the daily closes) retires the current demo world (state →
epilogue, `is_demo` unflagged) and seeds a fresh week-4 world with bot
history, so god-mode leftovers from visitors never linger more than a day.
The cron is a no-op unless `AGORA_DEMO_ENABLED=true` (set it on the worker
AND the api service), skips if the current demo world is under 20 hours old,
and needs the image to contain `tests/` + `scripts/` (the Dockerfile copies
both). Retired demo worlds accumulate as epilogue rows — harmless, but worth
an occasional cleanup.

Manual rotation (e.g. mid-day, after a workshop demo went feral) still works
from your machine through the PG public proxy:

```sh
cd backend
AGORA_DATABASE_URL="postgresql+asyncpg://postgres:<pw>@acela.proxy.rlwy.net:54660/railway" \
  .venv/bin/python scripts/reset_demo.py
```

(Password: Railway dashboard → Postgres → Variables, or `railway variables
--service Postgres`.)

`AGORA_DEMO_ENABLED=true` must be set on the api service for `/demo/*`
endpoints to work outside dev — and on the worker for the nightly rotation.

## Email (Monday Brief digests + magic links)

Both **api and worker** carry the email variables (worker sends the weekly
digests; api sends magic links and manual digest sends):

- `AGORA_EMAIL_PROVIDER=resend` (default `console` = compose + log only)
- `AGORA_RESEND_API_KEY` (set 2026-06-12 via CLI on both services)
- `AGORA_EMAIL_FROM` — currently `Agora <onboarding@resend.dev>`, Resend's
  sandbox sender. **Sandbox limitation: it only delivers to the Resend
  account owner's own email.** Before real instructors get digests, verify a
  sending domain at https://resend.com/domains and update this variable on
  both services.
- `AGORA_APP_BASE_URL=https://frontend-production-1bbf.up.railway.app` —
  used for links inside emails.

Failed sends are recorded in the `email_log` table (`status=failed`) and the
digest sweep retries on its next cron pass, so a bad sender config never
silently drops a week.

## Gotchas (learned the hard way)

- **Auto-deploy requires the Railway GitHub App.** Railway can build a
  public repo without it, but push webhooks only arrive if the app
  (github.com/apps/railway-app) is installed with access to the repo. Without
  it, sources connect and build once but never redeploy on push.
- **Auto-deploy requires a branch.** `connect_service_source` without
  `branch` deploys once and never again. If pushes stop deploying, reconnect
  the source *with* `branch: main` — that also force-builds the latest
  commit, which doubles as the manual deploy step of last resort.
- **No Railway healthcheck on api.** Railway's probe couldn't reach the
  IPv6-only uvicorn bind and failed deploys that were actually healthy, so
  `health_check_path` is empty. Verify health through the frontend proxy
  (`/api/health`) instead.
- **Never run `railway config apply` on this project.** The IaC round-trip
  mangles the template Postgres/Redis deploy config (destructive) and wants
  to delete anything it doesn't manage. All config is driven via CLI + MCP.
- **Local Docker vs Railway bind:** `BIND_HOST` defaults to `0.0.0.0`
  locally (Docker's DNS/port-publish are IPv4) and is set to `::` on Railway.
  Don't hardcode either.

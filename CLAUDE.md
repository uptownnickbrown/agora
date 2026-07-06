# CLAUDE.md

Agora is multiplayer economics courseware: a browser game where a class of
students trades in a live simulated market economy while an LLM tutor and a
mastery model turn play into graded evidence of learning. Solo project, moves
fast, deployed on Railway. `README.md` covers what's built; this file is the
orientation an agent needs to work in the code safely.

## Layout

- `backend/` — Python 3.11, FastAPI, SQLAlchemy 2 (async), Postgres in prod /
  SQLite in tests, Alembic migrations, an `arq` (Redis) worker for scheduled jobs.
  - `app/api/` — routers: `student`, `market`, `fun`, `tutor`, `instructor`,
    `admin`, `demo`, `ws`, `auth`.
  - `app/services/` — game logic: `market`/`engine/orderbook` (the double-auction
    matching + escrow — the money code), `close` (daily market close, the world
    heartbeat), `fun` (puzzle, fishing, haggling, streaks), `npc`, `shops`,
    `production`, `digest` (Monday Brief email), `worlds`, `auth`.
  - `app/pedagogy/` — `tutor` (Pip chat + tutor checks + LLM grading + on-the-fly
    question generation), `bank` (learning objectives + question bank),
    `puzzles`, `grades`, `playbook`, `openstax` (committed CC-BY course text).
  - `app/template.py` — the canonical game definition (goods, recipes,
    facilities, balance constants). **Source of truth**; the frontend has a
    hardcoded mirror in `places.tsx` that must be kept in sync by hand.
  - `app/worker.py` — cron jobs: `daily_market_close`, `fast_tick` (NPC orders),
    `email_sweep` (digests), `demo_reset` (nightly blue-green demo rotation).
  - `app/models.py` — one file, all tables. `World.config` is a JSON dict used
    as a keyed knob store (pacing, demo flags, digest stamps, grade weights).
  - `tests/` — pytest. `test_semester.py` runs a full 7-week simulation; the
    `game` fixture (`conftest.py`) gives a quiet week-2 world + 3 students.
  - `scripts/` — `seed_midcourse.py` (seeds a mid-course world through the real
    service layer; `demo_reset` calls it), `qa_screenshots.py`, asset gen.
- `frontend/` — React 18 + TypeScript + Vite, no state library. 9 files in
  `src/`. `api.ts` is the client; `App.tsx` the shell; `places.tsx`,
  `pip.tsx`, `study.tsx`, `town.tsx`, `instructor.tsx` the screens;
  `ui.tsx` the atoms; `theme.css` all styling. Painted assets in `public/assets`.
- `docs/` — `SPEC.md`, `DECISIONS.md` (founding rationale), `DEPLOY.md`
  (Railway runbook — read before touching prod), `INSTRUCTOR_AUTOMATION.md`.

## Running & verifying

- **Full stack locally:** `docker compose up -d --build` (Postgres, Redis,
  api on :8000, worker, frontend on :5173). Frontend changes need a
  `docker compose up -d --build frontend` rebuild (nginx image, no dev mount).
- **Backend tests:** `cd backend && .venv/bin/python -m pytest` (~20s, ~74
  tests). Always run before committing backend changes.
- **Frontend typecheck:** `cd frontend && npx tsc --noEmit`. No frontend tests
  or CI yet.
- **Seed QA/demo worlds:** see `agora-working-setup` memory / `scripts/`.

## Deploy

`git push origin main` → Railway rebuilds all three services (api, worker,
frontend) from GitHub. The api runs `alembic upgrade head` pre-deploy. New DB
tables need a migration in `backend/alembic/versions/` (chain from the current
head). Push over `ssh -o HostName=ssh.github.com -p 443` if port 22 is blocked.
Trigger a demo reseed without SSH/DB access via
`POST /api/admin/demo/rotate` with the `X-Agora-Ops-Token` header.

## Conventions & gotchas

- **Money and effort are integers; never mint or destroy them off-ledger.**
  Coin/inventory moves go through `services/common.py` helpers; the order book
  escrows on buy and refunds on cancel/expiry.
- **Mutating requests lock the acting player row** (`deps.py`, FOR UPDATE on
  non-GET). A GET that writes bypasses that lock — avoid it, or lock explicitly.
- **Every LLM path degrades gracefully** to canned/keyword output when no API
  key or the per-world daily token budget is exhausted. Keep that property.
- **No emojis as UI iconography** — use the painted asset pipeline; emojis are
  fine only in prose/Pip dialogue. Instructor-facing copy stays professional.
- Student-facing copy is whimsical (Professor Pip's voice); avoid em-dash
  chains and staccato-fragment marketing tone.
- The public landing page (`frontend/public/landing/`) is the product's litmus
  test — keep it in sync as features change.

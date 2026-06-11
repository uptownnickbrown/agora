# Agora

A multiplayer economic simulation that teaches introductory microeconomics by making
students live inside a working economy. A class of 20–80 students inhabits a shared
fantasy-flavored market town for ~7 weeks: gathering, crafting, trading on live
order-book markets, building production facilities — while every mechanic IS a
syllabus concept and an LLM tutor ("Professor Pip") weaves assessment into play.

- **Spec:** [docs/SPEC.md](docs/SPEC.md)
- **Founding decisions (stack, design calls):** [docs/DECISIONS.md](docs/DECISIONS.md)

## Status

Pre-Phase-0. The **headless economy harness is built and green** — per spec §14 item 15,
the simulation engine had to prove the promised classroom phenomena before any UI work:

| Phenomenon | Scenario | Result |
|---|---|---|
| CDA converges to competitive equilibrium | `convergence` | closes settle at p* ≈ 72 |
| Festival Rush: demand shock → spike → supply response → glut (Week 2) | `festival_rush` | 43 → 164 → 47, shortage visible at the peak |
| Bread Decree: drought → ceiling → empty shelves (Week 3) | `bread_ceiling` | volume 88→13/day, ~75 units/day unmet demand, seller withdrawal visible |
| Ceiling repeal restores the market | `test_ceiling_repeal_*` | trade resumes post-repeal |

A bonus emergent result: the bread ceiling suppresses bakers' grain bidding
(derived demand), starving the *input* market — unscripted, correct economics.

## Run the simulation harness

```bash
cd backend
pip install -e ".[dev]"   # or just: pip install pytest (engine has no deps)
python -m sim.run                  # all scenarios, day-by-day market tables
python -m sim.run festival_rush    # one scenario
python -m pytest                   # the Phase-0 economic gate, 3 seeds each
```

The engine (`backend/app/engine/`) is pure Python with zero dependencies — the same
code the production server will wrap with persistence and an API.

## Layout

```
backend/
  app/engine/      # the economy: order book, NPC schedules, agents, world ticks
  app/             # FastAPI app, SQLAlchemy models, ARQ worker (skeletons)
  sim/             # headless scenarios + runner (the balance laboratory)
  tests/           # order-book unit tests + the economic phenomena gate
frontend/          # React + Vite + TS placeholder
docs/              # SPEC.md, DECISIONS.md
docker-compose.yml # postgres + redis + api + worker + frontend
```

## Local stack

```bash
docker compose up --build
# api  -> http://localhost:8000/health
# app  -> http://localhost:5173
```

Database migrations: `cd backend && AGORA_DATABASE_URL=... alembic revision --autogenerate -m initial && alembic upgrade head` (first migration is generated against a live database rather than hand-written).

## Deploy

Three Railway services built from the two Dockerfiles (`backend` twice — the worker
service overrides the command with `arq app.worker.WorkerSettings` — plus `frontend`),
with Railway Postgres and Redis attached via `AGORA_DATABASE_URL` / `AGORA_REDIS_URL`.

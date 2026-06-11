# Agora

A multiplayer economic simulation that teaches introductory microeconomics by
making students live inside a working economy. A class of 20–80 students
inhabits a fantasy-flavored market town for seven weeks: gathering, crafting,
trading on live order-book markets, building facilities, fishing a doomed
commons — while every mechanic IS a syllabus concept, Professor Pip (an
LLM-backed tutor pigeon) weaves assessment into play, and the instructor runs
the world from a low-touch god-mode dashboard.

- **Spec:** [docs/SPEC.md](docs/SPEC.md)
- **Founding decisions:** [docs/DECISIONS.md](docs/DECISIONS.md)
- **Art pipeline:** [docs/ASSET_WISHLIST.md](docs/ASSET_WISHLIST.md)
- **Licensing/attribution:** [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md)

## What's built (everything in spec phases 0–3, v1 scope)

**Simulation layer** — continuous double-auction order books per good
(price-time priority, partial fills, escrow), NPC liquidity from configurable
supply/demand schedules that auto-scale with class size, production facilities
(3 tiers, upkeep, hired workers with diminishing returns), gathering with
aptitudes, hand-craft recipes, posted-price shops with price-sensitive NPC
retail, smog externalities + scrubbers, a logistic-regen fishery commons,
Crown licenses via sealed-bid auctions, compacts with zero enforcement, soft
bankruptcy via Guild loans, daily market close with OHLCV snapshots and the
Agora Crier's named-movers report.

**Pedagogy layer** — 29 learning objectives adapted from OpenStax Ch. 2–13,
36 context-triggered tutor checks (MCQ + LLM-graded free response with keyword
fallback), mastery EMA tracking, Professor Pip chat (Sonnet 4.6, prompt-cached,
budget-capped, canned degradation), proactive nudges, moment detection (price
spikes, concentration, shortages, seller withdrawal, cartel parallel pricing,
commons depletion, disengagement), one-click diegetic interventions (16 kinds,
previewable, schedulable), lecture playbook generator (Opus 4.8 polish
optional), gradebook (participation + mastery, CSV), mastery heatmap, and the
epilogue "Your Economic Story" recap.

**Fun layer** — Market Mastermind daily puzzle (seeded per world-day, heat
feedback, share cards, streaks), dockside fishing with trophies and stock-
dependent yields, the Traveling Merchant comparative-advantage onboarding,
achievements, earned prestige cosmetics + a coin-priced Luxury Boutique.

**The seven-week arc** ships as scripted world beats: Lantern Festival demand
shock (wk2), drought + Bread Decree price ceiling + repeal (wk3), Charter
Choice demand swing (wk4), two glowdye license auctions (wk5), Gray Skies smog
+ soot levy + fishery quota (wk6), and the Market Wars team tournament (wk7).

## Tests (49, all green)

```bash
cd backend
pip install -e ".[dev]" aiosqlite email-validator anyio
python -m pytest                 # engine + API + WS + admin (~15s w/o slow)
python -m pytest tests/test_semester.py   # the FULL SEMESTER (~70s):
```

`test_semester.py` is the crown jewel: 12 scripted bot students (traders,
producers, anglers, license tycoons, cartelists) play all 49 days through the
real service layer, and the test asserts every week's promised phenomenon
actually emerges — festival spike, decree shortage and repeal recovery,
monopoly margins compressed by entry, fishery decline and post-quota recovery,
smog, cartel detection, tournament, and grading artifacts built from real data.

The pure-engine harness (`backend/sim/`) remains the balance laboratory:

```bash
python -m sim.run                # day-by-day tables for all scenarios
```

## Run it

```bash
docker compose up --build
# app  -> http://localhost:5173   (vite dev: cd frontend && npm i && npm run dev)
# api  -> http://localhost:8000/docs
```

Local dev without Docker:

```bash
cd backend && pip install -e .
AGORA_ENV=dev AGORA_DATABASE_URL=sqlite+aiosqlite:////tmp/agora.db \
  uvicorn app.main:app --reload     # auto-creates schema on SQLite
cd frontend && npm install && npm run dev
```

**One-click demo:** seed a demo world (`cd backend && .venv/bin/python
scripts/seed_midcourse.py --suffix demo --week 4 --demo`), then visit
`http://localhost:5173/?demo=student` or `?demo=instructor` — you land in the
live world as a fresh visitor merchant (or its instructor) with Pip's guided
tour. The landing page (`/landing/`) has both buttons. Enabled in dev or with
`AGORA_DEMO_ENABLED=true`.

Demo-world safety: every student click mints its own visitor merchant (two
simultaneous visitors simply meet in the same market — that's the product);
god mode is shared, so lifecycle controls (close day / advance week / end
world) are disabled there while interventions stay live. Reset the shared
world anytime (or nightly via cron for a public demo) with
`scripts/reset_demo.py`, which retires the old world and seeds a fresh one.

**QA testbeds:** `scripts/seed_midcourse.py --suffix wN --week N` seeds any
course week with 12 bot students (accounts `qa{sfx}.*@agora-u.edu`, password
`agora-qa`); `scripts/qa_screenshots.py` sweeps a 40+ shot matrix (both roles
× desktop/phone × clean/mid/late course, including a scripted god-mode
disruption) into `qa/shots/`.

Or by hand: register → "Create a world" (you become its instructor) → open a
private window, register a student, join with the code → trade against the
NPC book → in god mode, run "daily close" to advance the world. The tutor runs canned
until `AGORA_ANTHROPIC_API_KEY` is set (Haiku 4.5 classification, Sonnet 4.6
tutoring, Opus 4.8 playbooks — DECISIONS.md #7).

## Layout

```
backend/
  app/engine/      # pure CDA matching engine (shared by server + harness)
  app/services/    # markets, worlds, production, shops, npc, close, detectors,
                   # interventions, licenses, compacts, fun, stats, auth
  app/pedagogy/    # LO graph + question bank, Pip, grades, playbook, recap
  app/api/         # auth, student, market, fun, tutor, instructor, admin, ws
  app/template.py  # the "Agora Standard 7-Week" world definition
  sim/             # headless balance harness
  tests/           # 50 tests incl. the full-semester simulation (bots.py)
frontend/          # React SPA, parchment-on-felt design system, PWA manifest
docs/              # SPEC, DECISIONS, ASSET_WISHLIST, ATTRIBUTION
```

## Deploy (Railway)

Three services from two Dockerfiles: `backend` as **api** (default CMD) and as
**worker** (`arq app.worker.WorkerSettings` — daily close at 11:59pm ET, NPC
refresh every 5 min), plus `frontend` (nginx serving the SPA and proxying
`/api` + WebSockets). Attach Railway Postgres/Redis via `AGORA_DATABASE_URL` /
`AGORA_REDIS_URL`; run `alembic revision --autogenerate -m initial && alembic
upgrade head` once against the live database.

## Known v1 edges (documented, deliberate)

- LTI 1.3 is a fast-follow; the grade model is LTI-shaped (DECISIONS #2/§8).
- WebSocket fanout is in-process; the `bus.publish` seam is where Redis pub/sub
  lands when the API scales past one process.
- Postgres row-level security is planned; tenancy is enforced in queries today.
- Email delivery for magic links is a stub (dev returns the token; wire an
  SMTP/provider sender for production).
- Web-push notification keys/wiring (PWA manifest ships; subscription endpoint
  is Phase-3.5 work).

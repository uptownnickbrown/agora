# Agora — Founding Decisions (ADR-000)

Decisions resolved in the founding design interview (2026-06-11), covering every open
question in spec §14. Each entry is binding until explicitly revisited; changes get a new
dated entry, not an edit.

## 1. Stack & hosting
- **Backend:** Python 3.11, FastAPI + SQLAlchemy 2.0 + Alembic, Pydantic v2 schemas.
  The OpenAPI schema is the contract: the frontend consumes a generated typed client.
- **Workers:** ARQ (Redis-backed) for per-World tick jobs (daily close, fast tick).
- **Frontend:** React + Vite + TypeScript SPA. PixiJS later where juice demands it.
- **Data:** PostgreSQL (single source of truth), Redis (cache/queues/pub-sub).
- **Deploy:** Dockerized services (api, worker, frontend) on Railway, with Railway
  Postgres + Redis. docker-compose for local dev.
- Rationale: author preference for Python + containers; matching-engine throughput at
  v1 scale (tens of orders/sec peak) is nowhere near Python's limits; the LLM/pedagogy
  tooling ecosystem favors Python.

## 2. Auth
- **Roll our own.** Magic-link email login as the primary flow, optional password
  (argon2), join-by-code enrollment, server-side sessions in Postgres.
- No managed auth provider: per-MAU pricing scales badly across churned semester
  cohorts and adds a subprocessor to institutional security reviews.
- No `.edu` restriction; the join code is the enrollment gate.
- Dual-enrollment minors: students are 13+, so COPPA does not apply; FERPA-mindset
  data handling (no assessment data visible to peers, export/delete per user) from day one.
- LTI 1.3 is a fast-follow; the identity model must accommodate an LTI identity source later.

## 3. Market institution (Phase 0)
- **Full continuous double auction from Phase 0.** No daily call-auction simplification —
  it would test the wrong product (the fun proof depends on live fills and moving charts).
- Limit + market orders, partial fills, price-time priority, order expiry ≤ 48h,
  all matching server-side in a transaction. Trade price = resting order's price.
- Money is integer **coppers** everywhere. No floats in economic state.

## 4. Labor (Week 4)
- **NPC workers only in v1.** Hiring NPC labor at a posted wage delivers the pedagogy
  (variable input, diminishing marginal returns, wage = marginal cost).
- Student-to-student effort contracting is deferred to v2 as an instructor-togglable
  module (collusion/integrity surface too large for v1 detectors).

## 5. Student-to-student communication
- **Structured only:** direct trade offers, compact proposals with formal terms (Week 7),
  canned emotes. No free-text chat in v1 → no moderation burden.
- Accepted trade-off: cartel negotiation happens off-platform (class Discord); our
  detectors see resulting behavior, not the talk. The trade-offer entity carries an
  optional message field in the schema, disabled in v1, so per-World chat can be enabled
  later without migration.

## 6. Teams
- **Light affiliation from Week 1, no shared economy.** Cosmetic houses (banner, name,
  house leaderboard that sums individual scores) for social glue. No shared assets,
  treasury, or production until the Week 7 tournament, where houses become the
  tournament teams.
- Schema: `Team` table + nullable `Player.team_id` from day one.
- Rationale: Weeks 1–6 phenomena (comparative advantage, monopoly, fishery collapse)
  require individual incentives; the fishery only collapses if self-interest is individual.

## 7. Tutor LLM mix & budget
- **Haiku 4.5** (`claude-haiku-4-5`): nudge eligibility/classification, canned-content selection.
- **Sonnet 4.6** (`claude-sonnet-4-6`): Professor Pip tutoring conversations + rubric
  grading of short free responses.
- **Opus 4.8** (`claude-opus-4-8`): weekly lecture playbook generation and epilogue
  "Your Economic Story" recaps (low volume, instructor/keepsake quality).
- Aggressive prompt caching on Pip's system prompt + week LO context (stable prefix
  first, volatile student state after the last cache breakpoint).
- **Budget: $50–100/month per 50-student World** (~$1–2/student/month) at spec'd usage.
  Per-World daily token ceilings with graceful degradation to canned content.

## 8. Real-time transport
- **WebSockets from day 1** (order-book diffs, trade tape, price ticker, notifications),
  fanned out via Redis pub/sub. Order placement remains plain HTTP POST.

## 9. Daily puzzle
- **Procedural templates + authored ramp.** 3–4 puzzle templates (mystery-price
  deduction first; shift-the-curve and arbitrage-route later) with procedural parameter
  generation and a difficulty validator, seeded per World-day so the whole class gets
  the same puzzle. First ~14 puzzles hand-authored as the tutorial ramp and quality bar.

## 10. Cosmetics economy
- **Hybrid.** Prestige cosmetics (titles, trophies, mastery-tier merchant outfits) are
  earned-only and visibly so. A coin-priced **Luxury Boutique** sells purely decorative
  shop bling — deliberately doubling as (a) the economy's coin sink for inflation
  control and (b) a live luxury/elastic-demand laboratory (Week 3). The two registries
  are visually distinct: learned players look accomplished, rich players look rich.

## 11. Trade tape identity
- **Anonymous live, named in the Crier.** The live order book and trade tape are
  anonymized; the Crier's daily market report names big movers narratively
  ("House Tanaka took 60% of today's iron"). Drama is curated at the daily-close rhythm,
  making the Crier appointment reading. Instructor dashboard always sees full named data.

## 12. Tiny classes (<15 students)
- **NPC liquidity auto-scales with roster size; no hard minimum.** Below ~12 students
  the instructor sees a soft "thin world" warning that some phenomena (fishery collapse,
  cartel formation) will be NPC-assisted rather than emergent. Week 6/7 event scripts
  carry NPC-participation fallbacks so story beats still land.

## 13. Mobile
- **Responsive web, phone-first** (every screen passes the 30-second dining-hall test),
  installable **PWA** + web push for daily-close/Crier/streak notifications.
  One-time in-app add-to-home-screen prompt (iOS web push requires it). No app stores in v1.

## 14. Name
- Keep **"Agora"** as the working title. Known collision risk (Agora.io et al.) —
  trademark check is a Phase 3 gate before any external pilot. No brand-critical
  identifiers in code (package names stay neutral).

## 15. Economic coherence (spec §14 item 15)
- **The headless sim harness is built first** (this commit): a pure-Python deterministic
  economy engine (`backend/app/engine/`) driven by scripted student bots and NPC
  schedule traders (`backend/sim/`), fast-forwarding multi-week scenarios.
- Phase-0 gate: the harness must demonstrate, with ~30 bot students,
  (a) **Festival Rush** — announced demand shock → price spike → lagged supply
  response → post-festival glut; and
  (b) **Bread Decree** — drought supply shock → price spike → price ceiling →
  visible shortage (unfilled demand, seller withdrawal).
  Both are asserted in `backend/tests/test_scenarios.py` and runnable via
  `python -m sim.run`.

## Architecture invariants (restated from spec, now binding)
- Authoritative modular monolith; every economically meaningful action is an immutable
  row in an append-only `econ_events` log (event-sourcing-lite); normalized tables are
  a projection.
- Hard multi-tenancy: every World-scoped row carries `world_id`; all queries filter by
  it; Postgres RLS planned.
- All economy logic consumes World-local logical time (per-World clock).
- The simulation engine is pure and DB-free; the server wraps it. The same engine code
  runs in production and in the harness.

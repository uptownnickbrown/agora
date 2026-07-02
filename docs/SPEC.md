# AGORA — Build Specification v1.0

*A multiplayer economic simulation game that teaches introductory microeconomics by making students live inside a working economy.*

**Document purpose:** This is the founding spec. Decisions from the founding interview are recorded in DECISIONS.md, which takes precedence where the two differ.

**Working title:** "Agora" (the ancient Greek marketplace). Placeholder — easy to rename.

-----

## 1. Vision & Product Thesis

Agora is a persistent, multiplayer, web-based economic simulation that replaces the textbook-and-problem-set experience in an introductory microeconomics course. A class of ~20–80 students inhabits a shared fantasy-flavored market economy for roughly 7 weeks of a semester. Students gather resources, craft goods, trade in live markets, build production facilities, and compete on leaderboards. Every core game mechanic IS a microeconomics concept: prices emerge from real student supply and demand, scarcity is real, trade-offs are felt, monopolies actually form.

The instructor does not play the game. The instructor is a low-touch god: a dashboard surfaces interesting economic moments happening in the class economy, offers one-click interventions ("trigger a drought," "impose a price ceiling on bread," "grant 5 dye licenses"), and generates lecture-prep playbooks ("your students just lived through a supply shock — here's the data, here's what to teach Monday").

An embedded LLM-backed tutor character weaves instruction and assessment into play, so an hour in the game is an hour of genuine learning that doesn't feel like homework.

**Business thesis:** This is a product, not a one-off course tool. It must be multi-tenant from day one in its data model (multiple professors, multiple institutions, simultaneous course sections), sold eventually as courseware that pairs with the free OpenStax *Principles of Microeconomics* textbook. Build once, teach every semester, license to other instructors.

**Three-layer mental model:**

1. **The Simulation Layer** — the authoritative server-side economy engine. Goods, markets, production, players, prices. This is "physics."
2. **The Pedagogy Layer** — reads the simulation, never IS the simulation. Event detection, embedded assessment, the AI tutor, mastery tracking, instructor dashboard, lecture playbooks.
3. **The Fun Layer** — engagement mechanics with no (or incidental) learning objective: daily puzzle, fishing minigame, crafting aesthetics, cosmetics, streaks, shop decoration.

A student should log in because of Layer 3, stay because of Layer 1, and learn because of Layer 2.

-----

## 2. Product Principles

1. **The economics must be real.** Prices are set by actual student order flow, not scripted curves. When the simulation needs liquidity or a price floor of activity, NPC traders (bots) participate in markets using configurable supply/demand schedules — this is also how instructor interventions get teeth.
2. **No filler game.** Every major system maps to a syllabus concept.
3. **Asynchronous-first.** Students play on their own schedule, 20–60 minutes a few times per week. No mechanic may require being online at a specific time, and no student may be irrecoverably ruined by being offline for 48 hours. Daily market-close ticks create rhythm without requiring synchronous play.
4. **Instructor time is precious.** Target instructor commitment: <30 min/week. Everything important is push-based.
5. **Transparent-ish god.** Interventions are diegetic: framed as in-world news ("The Royal Granary announces a price ceiling on bread!").
6. **Grades reward engagement and demonstrated understanding, not wealth.**
7. **Web first, API always.**

-----

## 3. Users & Roles

### 3.1 Student
- Belongs to exactly one **World** (a course section's economy instance) per course enrollment.
- Plays a merchant character: gathers, crafts, trades, builds, fishes, decorates, answers tutor checks.
- Sees: market UI, their inventory/shop, leaderboards, daily puzzle, tutor chat, their own mastery progress.
- Never sees: other students' grades, instructor dashboard, intervention controls.

### 3.2 Instructor
- Owns one or more Worlds (course sections).
- Sees: live economic dashboard, event/alert feed, intervention catalog, per-student engagement and mastery analytics, gradebook export, lecture playbook generator.
- Acts: triggers/schedules interventions, adjusts pacing, endorses tutor-suggested teachable moments, configures grading weights.

### 3.3 Platform Admin (us)
- Creates institutions/instructor accounts, manages templates, monitors system health, tunes economy balance parameters globally.

### 3.4 NPC Agents (system actors)
- Bot traders providing market liquidity and implementing interventions.
- The tutor character (Section 9).

-----

## 4. Pedagogical Framework & OpenStax Alignment

Pairing target: **OpenStax *Principles of Microeconomics 3e*** (CC BY). The game replaces most textbook-reading homework for covered weeks; lecture formalizes concepts using what just happened in the class economy.

### 4.1 Coverage map (OpenStax 3e chapters → game)

| OpenStax chapter | Game coverage |
|---|---|
| 1. Welcome to Economics | Onboarding week (implicit) |
| 2. Choice in a World of Scarcity | **Week 1** — core |
| 3. Demand and Supply | **Week 2** — core |
| 4. Labor and Financial Markets | Partial (Week 4 hiring mechanic) |
| 5. Elasticity | **Week 3** — core |
| 6. Consumer Choices | Woven through Weeks 1–3 |
| 7. Production, Costs and Industry Structure | **Week 4** — core |
| 8. Perfect Competition | **Week 5** — core |
| 9. Monopoly | **Week 5** — core |
| 10. Monopolistic Competition & Oligopoly | **Week 7** — core |
| 11. Monopoly and Antitrust Policy | Week 7 (antitrust intervention) |
| 12. Environmental Protection & Negative Externalities | **Week 6** — core |
| 13. Positive Externalities and Public Goods | Week 6 (commons/fishery; public works option) |
| 14–20 | Out of scope for v1 game weeks; taught conventionally |

### 4.2 Learning model
- **Experience first, formalize second.**
- **Embedded assessment, continuous and small:** 2–4 minute "tutor checks" triggered contextually (~8–12 graded micro-assessments per student per week), each tagged to a learning objective.
- **Mastery tracking:** per-LO rolling estimate; instructors see a class heatmap.
- **Borrowed experimental designs:** double auctions, pit markets, price-control experiments, common-pool resource games, sealed-bid auctions, Bertrand games.

-----

## 5. The Game World

### 5.1 Fiction & tone
A lightly fantastical pre-industrial market town ("the Agora"). No combat. The fiction makes goods, shocks, and institutions feel like a world: droughts, festivals, royal decrees, guild licenses. In-world news via "The Agora Crier." Tone: charming, a little funny.

### 5.2 Visual/UX direction (v1)
- Web app, responsive, mobile-browser friendly. 2D illustrated UI — board game energy (Splendor/Catan), not 3D. Navigation between *places* (Market Square, Your Shop, The Docks, The Commons, The Guild Hall, The Crier).
- Every screen: "could a distracted freshman on a phone understand and act in 30 seconds?"
- Juice matters: trade confirmations, crafting animations, price tickers, confetti.

### 5.3 Core student loop (~25 min session)
1. Daily puzzle (2 min) → streak credit.
2. Check the Crier: overnight close report, news, leaderboard movement.
3. Collect production output.
4. Decisions: post orders, start crafting, reallocate labor, upgrade.
5. Tutor surfaces one contextual check or insight.
6. Optional fun: fish, decorate, browse shops, structured trade offers.

### 5.4 The economy (Simulation Layer specifics)

**Goods.** ~12–16 goods in 3 tiers.
- *Raw*: grain, wood, ore, wool, fish, herbs.
- *Processed*: flour, lumber, iron, cloth, medicine.
- *Finished/luxury*: bread, tools, garments, tapestries (customizable artisan good), glowdye (license-gated, Week 5).

**Production.** Facilities (farm plot, mill, loom, smithy, workshop): build cost (fixed cost), per-cycle inputs + upkeep (variable cost), output per tick, upgrade tiers, finite capacity. Runs per tick whether or not the player is online.

**Labor/time budget.** Daily "effort" allotment (action points). The scarcity primitive. Does not stockpile beyond ~2 days.

**Markets.** Per-good continuous order-book market (continuous double auction). Price history charts are first-class UI.
- **Daily market close** (nightly tick): clears stale orders, snapshots official prices, leaderboards, facility payouts, Crier report.
- **NPC liquidity bots** with configurable reservation-price schedules.
- **Player shops**: posted-price retail channel; NPC retail demand sampled daily against price.

**Money.** Single currency ("coins," integer coppers). Equal starting endowment. No real money anywhere, ever.

**Anti-ruin.** Bankruptcy is a soft state: a "fresh start" Guild loan restores playability.

-----

## 6. The Seven-Week Arc

Weeks unlock on instructor pacing control (calendar default, manual advance allowed).

### Week 1 — Scarcity, Choice, and Gains from Trade *(Ch. 1–2; threads of 6)*
- Trading only — no production. Deliberately unbalanced endowments + gathering aptitudes so trade is obviously valuable.
- **Event: "The Traveling Merchant"** — comparative-advantage onboarding puzzle (limited cargo, different local prices, route choices); completing it funds your first shop.
- Assessment: opportunity cost, specialization, gains from trade, budget constraints.

### Week 2 — Demand and Supply *(Ch. 3)*
- Unlocks: tier-1 facilities, full order-book UI with charts.
- **Event: "The Festival Rush"** — Lantern Festival announced 4 days out; NPC demand for garments/bread spikes hard, then vanishes. Shortage → price spike → supply response → post-festival glut.
- Interventions: festival magnitude; optional mid-week wool blight (supply-shift contrast).
- Assessment: demand vs. quantity demanded, shift vs. movement along, equilibrium, surplus/shortage — using the class's own price charts.

### Week 3 — Elasticity & Price Controls *(Ch. 5; 6 threads)*
- Unlocks: medicine (inelastic NPC demand) vs. elastic luxuries (tapestries).
- **Event: "The Drought" + "The Bread Decree"** — drought hits grain; bread spikes; Crown imposes a price ceiling on bread at the old price → shelves empty; gray market may emerge (let it). Medicine, uncapped, stays expensive but available.
- Interventions: the ceiling (one click); optional wool price floor; ceiling repeal as resolution.
- Assessment: elasticity determinants, who bears price-control costs, deadweight loss intuition, total revenue test.

### Week 4 — Production, Costs, and the Firm *(Ch. 7; Ch. 4 thread)*
- Unlocks: facility tiers 2–3, automation, hiring NPC workers at a wage (diminishing marginal returns).
- **Event: "The Charter Choice"** — Guild charter factory (high fixed/low marginal) vs. artisan (low fixed/high marginal); instructor swings demand down then up. Predict-then-observe break-even journaling.
- Assessment: fixed/variable/marginal cost, average cost curves, diminishing returns, shut-down vs. exit, break-even.

### Week 5 — Perfect Competition vs. Monopoly *(Ch. 8–9)*
- Unlocks: **Glowdye licensing** — Crown sealed-bid auction of 4–6 exclusive licenses. License holders face posted NPC demand + student demand; everyone else trades in thick competitive markets.
- **Event: "The Second Charter"** — more licenses announced; harvest surplus now vs. price low for loyalty; entry compresses margins toward competitive outcome.
- Interventions: number/timing of new licenses; optional antitrust suit.
- Assessment: price taker vs. maker, barriers to entry, MR < P intuition, entry and profits, consumer surplus transfer.

### Week 6 — Externalities and the Commons *(Ch. 12–13)*
- Unlocks: production **smog** (district-level efficiency penalty + luxury demand hit; scrubbers purchasable), **The Commons** fishery with regeneration rate, open access.
- **Events:** "The Gray Skies" (art desaturates as smog accumulates) and "The Fishery Collapse" (it WILL collapse; let it). Resolution: Pigouvian smog tax; fishery quotas/tradable permits.
- Assessment: private vs. social cost, tragedy of the commons, corrective taxes vs. quotas vs. property rights, public goods/free riding (optional lighthouse subscription).

### Week 7 — Strategic Behavior, Oligopoly, and the Grand Tournament *(Ch. 10–11)*
- Unlocks: **Compacts** — formal agreements with visible terms and *no enforcement*. Artisan differentiation matures (monopolistic competition).
- **Event: "The Market Wars"** — 4-day team capstone tournament. Cartels form and collapse, price wars, entry deterrence, defection. Antitrust lever + Crier reporting make strategy public.
- Assessment: oligopoly interdependence, collusion incentives, prisoner's dilemma, differentiation, antitrust rationale.
- **End of term:** epilogue state — read-only economy museum; per-student auto-generated "Your Economic Story" recap.

-----

## 7. The Fun Layer

1. **The Daily Ledger Puzzle** — NYT-energy daily puzzle, same for the whole class, ~2 min. v2: "Common Threads," Connections-style — 16 econ/Agora terms, four hidden groups of four, four mistakes; hand-written bank in `app/puzzles.py`; shareable emoji result card; streak leaderboard; effort reward with a flawless bonus. (v1 "Market Mastermind" price-deduction retired 2026-07: it read as homework, not play.)
2. **Fishing** — suspense minigame at The Docks: cast, nibble fake-outs, strike, reel, reveal (named species, per-fish weights, personal bests, rare trophies). Outcomes are server-rolled at cast time; the strike timing is theater. Costs effort. On-ramp to Week 6 commons.
2b. **The haggling caravan** — one visitor per merchant per day with a hidden reservation price and three quotes to strike a deal (surplus made visceral). Reveal their limit when the table clears; "Silver Tongue" achievement for capturing ~all of it.
2c. **The daily streak chest** — small coin grant on the first visit of each world day, growing with consecutive days (starts on day 2; capped at 25c).
3. **Artisan crafting** — tapestry/garment pattern designer; maker's mark; price premiums (differentiation); class gallery.
4. **Shop & character customization** — earned prestige cosmetics + coin-priced Luxury Boutique (see DECISIONS.md #10).
5. **Achievements & titles** — "Cloth Baron," "Master Angler," "Arbitrage Artist," "Survived the Drought."
6. **Streaks & dailies** — capped effort bonuses; never punishing enough that a missed weekend matters.

-----

## 8. Assessment, Grading, and Mastery

- **LO graph** seeded from OpenStax 3e Ch. 2,3,5,6,7,8,9,10,11,12,13 objectives (CC BY, with attribution). Node: id, chapter ref, week mapping, mastery rubric.
- **Tutor checks:** MCQ, graph-taps, predict-then-observe, one-sentence free responses graded by LLM with rubric. 1–2 LOs each. Triggered by gameplay context (best), daily cadence floor (fallback), event aftermaths.
- **Participation score:** session regularity, market activity, event participation, puzzle streaks — engagement, not wealth. Diminishing returns on action spam.
- **Mastery score:** per-LO rolling estimate, recency-weighted; wrong-then-right counts as growth.
- **Gradebook:** instructor-configured weights; CSV export. LTI 1.3 fast-follow, grade model LTI-compatible from day one.
- **Integrity:** low-stakes frequent checks (cheating ROI terrible by design); multi-accounting/collusion detection in the anomaly system.

-----

## 9. The Tutor — "Professor Pip" (a know-it-all market pigeon)

LLM-backed (Anthropic API), chat dock + contextual popups.

**Modes:** reactive Q&A (Socratic, in-world, never trades for the student, never leaks hidden info), proactive nudges (rate-limited, dismissible), assessment delivery (in character, instant feedback).

**Context assembly per call:** student's recent actions + holdings, relevant market state, current week's LOs, mastery profile, conversation history. System prompt enforces pedagogy-first, no financial advice that plays the game for them, escalate out-of-scope.

**Cost control:** model tiering + caching + per-student daily budgets (see DECISIONS.md #7).

-----

## 10. Instructor God Mode

### 10.1 Dashboard (5-minute check-in)
World vitals (actives, price charts, wealth Gini, volumes, smog/fishery), the Feed (events, detected moments, interventions), class heatmap (LO mastery × student; engagement flags).

### 10.2 Moment detection
Rules + anomaly engine: price spike/crash (z-score), market concentration, hoarding/corners, spread blowouts, liquidity droughts, cartel signatures, commons depletion velocity, engagement anomalies, gray markets after price controls, suspicious wealth transfers (integrity).

### 10.3 Intervention catalog (one-click, diegetic, parameterized, previewable)
Supply shocks (drought/blight/bumper), demand shocks (festival/foreign buyer/craze), price ceiling/floor, taxes/subsidies (incl. Pigouvian), licenses/antitrust, commons policy (quotas/permits/seasons), money/credit (sparingly), custom raw parameters (gated).

### 10.4 Lecture Playbook generator
Weekly: what happened (with charts), 3–5 discussion questions keyed to real decisions, concepts to formalize, misconceptions detected, suggested next-week interventions. Slides-friendly markdown export.

-----

## 11. Multi-Tenancy & World Lifecycle

- **Hierarchy:** Institution → Instructor → Course → Section → **World**. No cross-World economic interaction in v1.
- **One canonical template** ("Agora Standard 7-Week"): goods tree, facility defs, NPC schedules, week gates, event scripts, LO graph, balance params. Instructor knobs: start date, pacing, class-size NPC scaling, grading weights, optional modules. Resist configuration sprawl.
- **Lifecycle:** Draft → Onboarding → Active (weeks 1–7) → Tournament → Epilogue (read-only) → Archived. Roster via email invite/join code.
- **Clock:** per-World logical clock; all economy logic consumes World-local time.

-----

## 12. Technical Architecture

See DECISIONS.md #1 for the resolved stack.

### 12.1 Shape
Authoritative backend monolith (modular) + SPA client + workers + LLM service module. **Determinism & audit:** every economically meaningful action is an immutable event in an append-only log; normalized tables are projections; the log powers replay, moment detection, analytics, playbooks, dispute debugging.

### 12.2 Tick model
- **Continuous:** order matching, trades, craft starts — immediate, server-authoritative.
- **Daily Market Close (per World):** production payout, upkeep, NPC schedule updates, order expiry, price snapshot (OHLCV), leaderboards, smog/fishery step, Crier report, streaks, scheduled interventions.
- **Fast tick (~5 min):** NPC order refresh, moment-detector sweep, nudge eligibility.

### 12.3 Market engine
Per-good order book: limit orders (price, qty, expiry ≤ 48h), market orders, partial fills, price-time priority; matching in a transaction; fills emit trade events. NPC traders = accounts whose orders derive from configurable piecewise-linear supply/demand schedules with noise; interventions mutate schedules. Shops: posted-price listings; NPC retail demand sampled daily.

### 12.4 API surface
Auth/roster; student (world state, inventory, facilities, orders, craft/build/upgrade/hire, shop CRUD, fishing/puzzle, tutor chat streaming, notifications); markets (book snapshot + diff stream, history, anonymized tape); instructor (dashboard, feed, detectors, interventions preview/execute/schedule, pacing, roster, analytics, gradebook, playbook); admin.

### 12.5 Data model (core entities)
`Institution, User, Enrollment(role), Course, Section, World, WorldClock, GoodDef, FacilityDef, RecipeDef, LicenseDef, EventScript, Team, Player, Inventory, Facility, CraftJob, Order, Trade, Shop, ShopListing, NPCAgent, NPCSchedule, Compact, PriceSnapshot, EconEvent, Intervention, DetectedMoment, LearningObjective, TutorCheck, TutorCheckAttempt, MasteryEstimate, TutorConversation, Achievement, PlayerAchievement, PuzzleDef, PuzzleAttempt, Streak, Notification, GradeConfig, GradeSnapshot.`
Def-tables template-scoped; instance tables World-scoped with hard tenancy isolation (world_id on every row, RLS planned).

### 12.6 Non-functional requirements
- Scale v1: 10 concurrent Worlds × 80 students; <200ms order ack.
- FERPA-mindset; WCAG AA intent (no color-only cues); rate limits; server-side validation; profanity filtering on named content; LLM cost ceilings with graceful degradation.

-----

## 13. Build Phasing

**Phase 0 — The Fun Proof:** single hardcoded World, auth, goods/inventory, order-book market with charts, facilities tier 1, daily close, NPC bots, Festival Rush, daily puzzle, fishing, basic shop. Success: ~10 adult playtesters voluntarily log in 4+ days running and report the trading is fun. **Headless sim harness built first** (done — see backend/sim/).

**Phase 1 — The Learning Proof:** tutor (reactive + checks), LO graph Weeks 1–3, mastery tracking, Weeks 1–3 content, basic instructor dashboard + 5 interventions.

**Phase 2 — The Course Proof:** Weeks 4–7, playbook generator, gradebook, full intervention catalog, epilogue.

**Phase 3 — The Product Proof:** multi-tenant self-serve UX, template knobs, admin tooling, LTI 1.3, pilot with 1–2 real sections.

-----

## 14. Open Questions — RESOLVED

All resolved in the founding interview; see **docs/DECISIONS.md**.

## 15. Appendix: Design Lineage
Continuous double auction (Vernon Smith), pit market/price-control experiments, common-pool resource games, sealed-bid auctions/Bertrand games; Splendor/Catan/idle-game/Wordle DNA; OpenStax *Principles of Microeconomics 3e* (CC BY 4.0).

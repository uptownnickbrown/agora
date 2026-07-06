"""Hand-polished lecture playbooks and Monday Brief for the demo world.

The demo world reseeds nightly from a pinned RNG seed ("agora-demo" in
scripts/seed_midcourse.py), so its 25-day history is identical every time:
the same drought on Day 16, the same flour corner by Jordan P., the same
bread ceiling and repeal. That determinism is what makes it safe to commit
these artifacts — every number below is real output from that seed, curated
once so demo visitors always see the product at its best, instantly, with no
LLM latency or per-visit spend.

If the simulation balance or the seeder changes, regenerate: seed a world
with --demo, hit /instructor/playbook?week=3|4 and /instructor/digest/preview,
and re-polish by hand.
"""
from __future__ import annotations

DEMO_PLAYBOOKS: dict[int, str] = {
    3: """# Lecture Playbook — Week 3
*Elasticity and price controls (OpenStax Ch. 5 & Ch. 3)*

## The week in one paragraph
Flour climbed 47% this week (147 → 216), and your class made every part of it
happen. Jordan P. saw the dry spell coming and quietly bought more than half
the flour trading on Days 15–17. Then the drought landed (Day 16), the Crown
capped bread at its pre-crisis price (Day 18), sellers pulled their loaves,
and flour kept running short: 30 units of unfilled demand on Day 18 against
two actual trades, 34 more on Day 20. The Decree was repealed on Day 21 to a
market the Crown called "baffling." Your students will not be baffled.

## What happened in your economy
- **Day 15** — Flour spiked to 147 (recent average 113) and bread to 398
  (average 252), *before any drought was announced*. Jordan P. bought 18 of
  the last 34 flour units traded (53%) and kept buying through Day 17.
- **Day 16** — The drought: "The fields crack and the grain withers." Grain
  supply collapses at the source; flour follows one step downstream.
- **Day 18** — The Bread Decree: "bread shall not exceed its old price!" A
  binding ceiling meets a supply shock, and the shelves empty within a day.
- **Days 18–20** — Flour runs 30–34 units short on volumes as thin as two
  trades a day. Nothing clears.
- **Day 21** — Repeal: "The Crown is baffled by empty shelves."
- All week, wool drifted 23 → 19 and wood eased to 18 — quiet gluts worth
  contrasting with the flour drama.

## Discussion questions
1. Flour spiked to 147 *before* the drought was announced. What did buyers
   know, and is "speculation" a demand shift or something else entirely?
2. Jordan P. held 53% of traded flour by Day 15. When does a big position
   become a corner — and what, in a market with free entry, would break it?
3. Trace the shock: drought → grain → flour → bread. Which curve shifted in
   each market, and why does a shortage travel downstream?
4. Under the Decree, who actually got bread? What did sellers do with loaves
   they refused to sell at the capped price?
5. Flour ran short for days while its price kept climbing. What was the
   price still allowed to do here that the bread price wasn't — and what
   should the morning after repeal look like?

## Misconceptions to address (lowest class mastery)
- **Budget constraints (58%).** Given goods prices and a coin budget,
  determine which bundles are affordable and how a price change re-tilts the
  tradeoff. Half the class can't yet see the budget line pivot when flour
  doubles. Two of the questions above are aimed squarely at this.
- **Price controls (72%).** Predict what a binding ceiling does: quantity
  traded, the shortage created, and who queues, rations, or exits. They
  lived it this week; now have them name it.
- **Comparative advantage (72%).** Two producers' opportunity costs → who
  specializes in what, and why both gain. Worth one worked example.
- **Deadweight loss (73%).** The trades that never happened under the Decree
  *are* the triangle. Have students count them from the tape.

## Suggested next moves
- Project the flour chart live in lecture and watch the post-repeal refill.
- Tee up the Charter Choice demand swing — Week 4's cost-structure decision.
""",
    4: """# Lecture Playbook — Week 4
*Production and costs (OpenStax Ch. 7)*

## The week so far
The drought's tail is still visible — flour ran 33 units short on Day 22 and
35 on Day 24 — while the goods that need cheerful shoppers softened: garments
fell to 193 (recent average 218) and wood slid to 17. A quiet spell settled
over the market on Day 24. That is exactly the weather for this week's
question: with revenue sagging, which facilities keep running at a loss, and
which should go dark for a night?

## What happened in your economy
- **Day 22** — Garments fell to 193 from a recent average of 218; flour
  still 33 units short on two trades.
- **Day 23** — Wood fell to 17 (average 19). The lumber glut meets softer
  demand.
- **Day 24** — "A quiet spell falls over the market." Demand ebbs
  economy-wide; flour runs 35 short anyway.

## Discussion questions
1. Garments glutted while flour starved — in the same week. Which curves
   moved where, and why can both happen at once?
2. A Loom costs 120 coppers to build and 4 a night in upkeep. During the
   quiet spell, when is running it at a loss still the right call?
3. Have a charter-holder (high fixed, low marginal) and an artisan (low
   fixed, high marginal) compare their week. Who hurts more in a slump?
4. Find a facility that idled this week. Shutdown logic, or panic?
5. Flour has now run short for ten days. What does it take to bring a Mill
   online, and what does that entry lag do to prices in the meantime?

## Misconceptions to address (lowest class mastery)
- **Budget constraints (58%).** Still the class's soft spot from Week 1 —
  a five-minute worked example pays for itself here.
- **Shutdown logic (66%).** Operate at a loss, shut down for now, or exit:
  the fixed-versus-avoidable-cost line your students are living this week.
- **Price controls (72%).** The Decree is gone; make sure the lesson stayed.
- **Comparative advantage (72%).** Resurfaces in the Charter Choice — who
  should hold a charter at all?

## Suggested next moves
- Open the first glowdye license auction — Week 5's monopoly arc.
- Consider an antitrust warning: Jordan P.'s flour position from last week
  is still on the books.
""",
}

DEMO_BRIEF_WEEK = 3
DEMO_BRIEF_SUBJECT = "Monday Brief — Econ 101, Week 3: Flour up 47%"
DEMO_BRIEF_MD = """## The sixty-second version
- **Flour** climbed 47% this week (147 → 216) — a corner, a drought, and a
  bread ceiling, in that order.
- 12 students · participation 70% · mastery 74%.
- The tutor's weakest spot: **Budget constraints (58%)** — two of the
  discussion questions below are aimed at it.
- No one needs a nudge this week: all twelve students traded and answered
  tutor checks.

""" + DEMO_PLAYBOOKS[3] + """
The current gradebook is attached as CSV (imports directly into most LMS
gradebooks).
"""


def demo_playbook(week: int) -> dict | None:
    md = DEMO_PLAYBOOKS.get(week)
    if md is None:
        return None
    return {"week": week, "canned": True, "markdown": md}

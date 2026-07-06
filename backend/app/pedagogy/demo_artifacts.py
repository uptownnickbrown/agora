"""Hand-polished lecture playbooks and Monday Brief for the demo world.

The demo world reseeds nightly from a pinned RNG seed ("agora-demo" in
scripts/seed_midcourse.py), so its 25-day history is identical every time:
the same bread spike on Day 15, the same drought on Day 16, the same
ceiling and repeal. That determinism is what makes it safe to commit these
artifacts — every number below is real output from that seed, curated once
so demo visitors always see the product at its best, instantly, with no
LLM latency or per-visit spend.

If the simulation balance, the seeder, or the question bank changes,
regenerate: seed a world with --demo, build the live playbook/digest for
weeks 3-4 (pop is_demo in memory to bypass the canning), and re-polish by
hand. Keep the landing page's Monday Brief mockup in sync.
"""
from __future__ import annotations

DEMO_PLAYBOOKS: dict[int, str] = {
    3: """# Lecture Playbook — Week 3
*Elasticity and price controls (OpenStax Ch. 5 & Ch. 3)*

## The week in one paragraph
Flour climbed 32% this week (103 → 136), and it never once cleared: from Day
15 through Day 21, roughly 34 units of demand went unfilled every single day
against volumes as thin as two trades. Bread told the louder story, spiking
to 456 (recent average 270) the day *before* the drought was announced. The
Crown answered on Day 18 by capping bread at its old price, the shelves
emptied within a day, and the Decree was repealed on Day 21 to a market the
Crown called "baffling." Your students will not be baffled.

## What happened in your economy
- **Day 15** — Bread spiked to 456 (average 270) and flour to 103, before
  any drought was announced. Somebody smelled the dry wind coming.
- **Day 16** — The drought: "The fields crack and the grain withers." Grain
  supply collapses at the source; flour follows one step downstream.
- **Days 15–21** — Flour runs 33–35 units short every day, with only 2–4
  trades clearing. The price climbs to 136 and the shortage persists anyway.
- **Day 18** — The Bread Decree: "bread shall not exceed its old price!" A
  binding ceiling meets a supply shock, and the shelves empty within a day.
- **Day 21** — Repeal: "The Crown is baffled by empty shelves."
- Meanwhile the quiet gluts: wool drifted 25 → 22, wood to 18, grain to 22.
  One market starved while three glutted, and both halves are the lesson.

## Discussion questions
1. Bread hit 456 the day *before* the drought was announced. What did
   buyers know, and is "speculation" a demand shift or something else?
2. Flour ran about 34 units short every day for a week while its price rose
   from 103 to 136. Prices were free to move, so what was missing for the
   market to clear: information, time, or Mills?
3. Trace the shock: drought → grain → flour → bread. Which curve shifted in
   each market, and why does a shortage travel downstream?
4. Under the Decree, who actually got bread? What did sellers do with
   loaves they refused to sell at the capped price?
5. Wool slid from 25 to 22 the same week flour starved. Can a glut and a
   shortage be the same mechanism pointed in opposite directions?

## Misconceptions to address (lowest class mastery)
- **Elasticity drivers (59%).** Predicting elastic vs. inelastic demand
  from substitutes, necessity, and budget share. This week wrote the worked
  example: medicine stayed expensive but kept selling; luxuries cratered.
- **Scarcity & choice (63%).** Half the class still conflates scarcity with
  a shortage. This week handed you the perfect contrast: flour was SHORT (a
  price phenomenon, fixable by price); effort is SCARCE (a budget fact, not
  fixable at all).
- **Equilibrium (69%).** The pressure that pushes a strayed price back.
  Ask what the flour price was trying to do all week, and what kept the
  quantity from following.
- **Opportunity cost (70%).** Worth one worked example from the week: every
  effort point spent milling flour at 136 was a point not spent elsewhere.

## Suggested next moves
- Project the flour chart live in lecture and watch the post-repeal refill.
- Tee up the Charter Choice demand swing — Week 4's cost-structure decision.
""",
    4: """# Lecture Playbook — Week 4
*Production and costs (OpenStax Ch. 7)*

## The week so far
The drought's tail is still visible — flour ran 23 units short on Day 22, 35
on Day 23, and 33 on Day 24 — while wood slid to 17 and a quiet spell
settled over the market on Day 24. That is exactly the weather for this
week's question: with revenue sagging, which facilities keep running at a
loss, and which should go dark for a night?

## What happened in your economy
- **Day 22** — Wood fell to 17 (recent average 19); flour still 23 units
  short on two trades.
- **Day 23** — Flour 35 short again. A week of profitable milling and still
  no flood of new Mills: entry takes coins and courage.
- **Day 24** — "A quiet spell falls over the market." Demand ebbs
  economy-wide; flour runs 33 short anyway.

## Discussion questions
1. Wood glutted while flour starved — in the same week. Which curves moved
   where, and why can both happen at once?
2. A Mill costs 120 coppers to build and 4 a night in upkeep. Flour has
   been scarce for ten days. What does that entry lag do to prices in the
   meantime, and who is quietly collecting the difference?
3. During the quiet spell, when is running a facility at a loss still the
   right call? Say it in terms of tonight's revenue and tonight's
   avoidable costs.
4. Have a charter-holder (high fixed, low marginal) and an artisan (low
   fixed, high marginal) compare their week. Who hurts more in a slump?
5. Find a facility that idled this week. Shutdown logic, or panic?

## Misconceptions to address (lowest class mastery)
- **Elasticity drivers (59%).** Still the class's softest spot from last
  week; five minutes on medicine vs. tapestries pays for itself.
- **Scarcity & choice (63%).** Scarcity is not a shortage; the flour saga
  makes the cleanest contrast you will get all term.
- **Equilibrium (69%).** Why the flour price kept climbing and the market
  still didn't clear: adjustment takes time and entry.
- **Cost types (69%).** Fixed vs. variable vs. marginal, freshly relevant
  now that facilities are humming and the quiet spell is squeezing margins.

## Suggested next moves
- Open the first glowdye license auction — Week 5's monopoly arc.
- Consider a stimulus if the quiet spell overstays; the Crier will spin it.
""",
}

DEMO_BRIEF_WEEK = 3
DEMO_BRIEF_SUBJECT = "Monday Brief — Econ 101, Week 3: Flour up 32%"
DEMO_BRIEF_MD = """## The sixty-second version
- **Flour** climbed 32% this week (103 → 136) and still ran ~34 units short
  every single day — a drought, a bread ceiling, and a market that couldn't
  clear.
- 12 students · participation 71% · mastery 72%.
- The tutor's weakest spots: **Elasticity drivers (59%)** and **Scarcity &
  choice (63%)** — the discussion questions below are aimed at them.
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

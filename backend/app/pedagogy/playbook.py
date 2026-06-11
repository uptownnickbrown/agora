"""Lecture Playbook generator (spec §10.4): what happened in YOUR economy this
week, with charts data, discussion questions keyed to real student decisions,
detected misconceptions, and suggested next interventions. Optionally polished
by Opus; always functional without it.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..config import get_settings
from ..models import (
    CheckAttempt,
    DetectedMoment,
    Intervention,
    MasteryEstimate,
    PriceSnapshot,
    World,
)
from .bank import LEARNING_OBJECTIVES

WEEK_CONCEPTS = {
    1: ("Scarcity, opportunity cost, gains from trade (OpenStax Ch.1-2)",
        ["Ask three students what they gave up to get what they're holding.",
         "Map two students' aptitudes and show the comparative-advantage arithmetic."]),
    2: ("Demand, supply, equilibrium (Ch.3)",
        ["Project the garment chart from festival week — have the class narrate it.",
         "Which curve shifted at the announcement? At the supply response?"]),
    3: ("Elasticity and price controls (Ch.5, Ch.3)",
        ["Compare medicine vs tapestry revenue when prices spiked.",
         "Who actually got bread under the Decree? What did sellers do?"]),
    4: ("Production and costs (Ch.7)",
        ["Have a charter-holder and an artisan compare their cost structures.",
         "Find a facility that idled in the slump — was that the right call?"]),
    5: ("Perfect competition vs monopoly (Ch.8-9)",
        ["Chart glowdye margins before and after the Second Charter.",
         "Why couldn't anyone corner grain the way glowdye was cornered?"]),
    6: ("Externalities and the commons (Ch.12-13)",
        ["Plot the fish stock curve. Where did individual incentive diverge from the group?",
         "Compare scrubber adoption before and after the soot levy."]),
    7: ("Oligopoly, cartels, antitrust (Ch.10-11)",
        ["Reconstruct a compact's price discipline and its collapse from the tape.",
         "What would credible enforcement have changed?"]),
}


async def build_playbook(db: AsyncSession, world: World, week: int | None = None) -> dict:
    week = week or world.current_week
    day_lo, day_hi = (week - 1) * T.DAYS_PER_WEEK + 1, week * T.DAYS_PER_WEEK

    snaps = (
        await db.scalars(
            select(PriceSnapshot).where(
                PriceSnapshot.world_id == world.id,
                PriceSnapshot.world_day.between(day_lo, day_hi),
            ).order_by(PriceSnapshot.good_id, PriceSnapshot.world_day)
        )
    ).all()
    charts: dict[str, list] = {}
    for s in snaps:
        charts.setdefault(s.good_id, []).append(
            {"day": s.world_day, "close": s.close, "volume": s.volume,
             "unfilled": s.unfilled_demand})
    interesting = {
        g: pts for g, pts in charts.items()
        if any(p["unfilled"] > 20 for p in pts) or _moved(pts)
    } or dict(list(charts.items())[:4])

    moments = (
        await db.scalars(
            select(DetectedMoment).where(
                DetectedMoment.world_id == world.id,
                DetectedMoment.world_day.between(day_lo, day_hi),
                DetectedMoment.severity.in_(["notable", "alert"]),
            ).order_by(DetectedMoment.world_day)
        )
    ).all()
    interventions = (
        await db.scalars(
            select(Intervention).where(
                Intervention.world_id == world.id,
                Intervention.world_day.between(day_lo, day_hi))
        )
    ).all()

    # Misconceptions: LOs with the lowest average mastery + most-missed questions.
    lo_rows = (
        await db.execute(
            select(MasteryEstimate.lo_id, func.avg(MasteryEstimate.score))
            .where(MasteryEstimate.world_id == world.id)
            .group_by(MasteryEstimate.lo_id)
        )
    ).all()
    weak_los = sorted(lo_rows, key=lambda r: r[1])[:4]

    concept, base_questions = WEEK_CONCEPTS.get(week, ("", []))
    moment_questions = [
        f"Day {m.world_day}: {m.summary} — what model explains this?"
        for m in moments[:3]
    ]
    playbook = {
        "week": week,
        "concept": concept,
        "what_happened": [
            {"day": m.world_day, "kind": m.kind, "summary": m.summary} for m in moments
        ],
        "interventions": [
            {"day": i.world_day, "kind": i.kind, "crier": i.crier_copy} for i in interventions
        ],
        "charts": interesting,
        "discussion_questions": (moment_questions + base_questions)[:5],
        "misconceptions": [
            {"lo": lo_id, "text": LEARNING_OBJECTIVES[lo_id].text,
             "avg_mastery_pct": round((avg or 0) / 10)}
            for lo_id, avg in weak_los if lo_id in LEARNING_OBJECTIVES
        ],
        "suggested_next": _suggest_next(week),
    }
    playbook["markdown"] = await _render_markdown(world, playbook)
    return playbook


def _moved(pts: list[dict]) -> bool:
    closes = [p["close"] for p in pts if p["close"]]
    return bool(closes) and max(closes) > min(closes) * 1.3


def _suggest_next(week: int) -> list[str]:
    nxt = {
        1: ["Unlock production and let the first facilities go up.",
            "Schedule the Festival announcement two days before the rush."],
        2: ["Queue the drought, then the bread ceiling two days later.",
            "Optional: a wool price floor for the contrast case."],
        3: ["Repeal the ceiling in class, live, and watch the market refill.",
            "Tee up the Charter Choice demand swing."],
        4: ["Open the first glowdye license auction.",
            "Consider an antitrust warning if anyone is hoarding."],
        5: ["Let smog accumulate before taxing it — the contrast teaches.",
            "Don't save the fishery yet. Let it hurt a little."],
        6: ["Impose the soot levy mid-week; quota the fishery after the collapse.",
            "Brief the houses on tournament rules."],
        7: ["Run the tournament; end the world into epilogue and share recaps."],
    }
    return nxt.get(week, [])


async def _render_markdown(world: World, pb: dict) -> str:
    lines = [f"# Lecture Playbook — Week {pb['week']}",
             f"*{pb['concept']}*", "",
             "## What happened in your economy"]
    for item in pb["what_happened"] or [{"day": "-", "kind": "-",
                                         "summary": "A quiet week — markets converged peacefully. That's a lesson too."}]:
        lines.append(f"- **Day {item['day']}** ({item['kind']}): {item['summary']}")
    if pb["interventions"]:
        lines += ["", "## Interventions you ran"]
        for i in pb["interventions"]:
            lines.append(f"- Day {i['day']}: {i['kind']} — “{i['crier']}”")
    lines += ["", "## Discussion questions"]
    for q in pb["discussion_questions"]:
        lines.append(f"1. {q}")
    if pb["misconceptions"]:
        lines += ["", "## Misconceptions to address (lowest class mastery)"]
        for m in pb["misconceptions"]:
            lines.append(f"- {m['text']} — class average {m['avg_mastery_pct']}%")
    lines += ["", "## Suggested next moves"]
    for s in pb["suggested_next"]:
        lines.append(f"- {s}")
    md = "\n".join(lines)
    return await _polish(md) or md


async def _polish(md: str) -> str | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.model_playbook,
            max_tokens=2000,
            system="You polish lecture-prep notes for an econ professor. Keep ALL facts "
                   "and numbers exactly as given; improve flow and add one vivid teaching "
                   "hook per section. Return markdown only.",
            messages=[{"role": "user", "content": md}],
        )
        return next((b.text for b in response.content if b.type == "text"), None)
    except Exception:
        return None

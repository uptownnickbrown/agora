"""Gradebook: participation + mastery, instructor-weighted, CSV export.

Wealth is deliberately NOT a grade input (spec principle #6). The grade model
keys on user identity + score breakdown so LTI 1.3 can map onto it later.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MasteryEstimate, Player, PlayerDayStat, User, World
from .bank import LEARNING_OBJECTIVES, QUESTIONS

PARTICIPATION_TARGET_PER_DAY = 6  # points/day that earn full participation credit


def _roster_filter():
    """Instructor views show enrolled students only — no NPCs, and no demo
    drop-in visitors (they'd pile up as ghost rows in a shared demo world)."""
    return (~Player.is_npc, ~Player.is_visitor)


async def gradebook(db: AsyncSession, world: World) -> list[dict]:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id,
                                              *_roster_filter()))
    ).all()
    weights = (world.config or {}).get("grade_weights", {"participation": 0.5, "mastery": 0.5})
    days_elapsed = max(1, world.world_day)
    rows = []
    for p in players:
        part_points = await db.scalar(
            select(func.coalesce(func.sum(PlayerDayStat.participation), 0)).where(
                PlayerDayStat.world_id == world.id, PlayerDayStat.player_id == p.id)
        )
        participation = min(1.0, part_points / (PARTICIPATION_TARGET_PER_DAY * days_elapsed))
        mastery_rows = (
            await db.scalars(
                select(MasteryEstimate).where(MasteryEstimate.world_id == world.id,
                                              MasteryEstimate.player_id == p.id)
            )
        ).all()
        relevant = [lo for lo in LEARNING_OBJECTIVES.values()
                    if lo.week <= world.current_week]
        by_lo = {m.lo_id: m.score / 1000 for m in mastery_rows}
        mastery = (sum(by_lo.get(lo.id, 0.0) for lo in relevant) / len(relevant)) if relevant else 0.0
        total = weights.get("participation", 0.5) * participation + \
            weights.get("mastery", 0.5) * mastery
        user = await db.get(User, p.user_id) if p.user_id else None
        rows.append({
            "email": user.email if user else "",
            "merchant": p.merchant_name,
            "participation": round(participation, 3),
            "mastery": round(mastery, 3),
            "grade": round(total, 3),
            "los_assessed": len([lo for lo in relevant if lo.id in by_lo]),
            "los_total": len(relevant),
        })
    rows.sort(key=lambda r: r["merchant"].lower())
    return rows


def _csv_safe(value):
    """Defuse spreadsheet formula injection: a cell a user controls (a student's
    display name) that starts with = + - @ or a control char is treated as a
    formula by Excel/Sheets on open. Prefix such cells with a single quote so
    they render as literal text. Non-strings pass through untouched."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


async def gradebook_csv(db: AsyncSession, world: World) -> str:
    rows = await gradebook(db, world)
    fields = ["email", "merchant", "participation", "mastery", "grade",
              "los_assessed", "los_total"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_safe(row[k]) for k in fields})
    return buf.getvalue()


async def mastery_heatmap(db: AsyncSession, world: World) -> dict:
    """LO × student grid for the instructor dashboard, with per-objective
    class aggregates and sample assessment items for the drill-down panel."""
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id,
                                              *_roster_filter())
                         .order_by(Player.merchant_name))
    ).all()
    relevant = [lo for lo in LEARNING_OBJECTIVES.values() if lo.week <= world.current_week]
    grid = []
    for p in players:
        rows = (
            await db.scalars(
                select(MasteryEstimate).where(MasteryEstimate.world_id == world.id,
                                              MasteryEstimate.player_id == p.id)
            )
        ).all()
        by_lo = {m.lo_id: m.score for m in rows}
        scores = {lo.id: by_lo.get(lo.id) for lo in relevant}
        assessed = [s for s in scores.values() if s is not None]
        grid.append({
            "merchant": p.merchant_name,
            "scores": scores,
            "avg": round(sum(assessed) / len(assessed) / 10) if assessed else None,
            "assessed": len(assessed),
        })

    los = []
    for lo in relevant:
        cells = [s["scores"][lo.id] for s in grid if s["scores"][lo.id] is not None]
        items = [q for q in QUESTIONS.values() if lo.id in q.los]
        los.append({
            "id": lo.id, "text": lo.text, "short": lo.short,
            "bloom": lo.bloom, "week": lo.week,
            "class_avg": round(sum(cells) / len(cells) / 10) if cells else None,
            "assessed": len(cells),
            "item_count": len(items),
            "sample_items": [q.prompt for q in items
                             if q.kind == "mcq"][:2],
        })
    all_cells = [c for s in grid for c in s["scores"].values() if c is not None]
    return {
        "los": los,
        "students": grid,
        "class_avg": round(sum(all_cells) / len(all_cells) / 10) if all_cells else None,
    }

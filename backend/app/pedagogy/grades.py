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
from .bank import LEARNING_OBJECTIVES

PARTICIPATION_TARGET_PER_DAY = 6  # points/day that earn full participation credit


async def gradebook(db: AsyncSession, world: World) -> list[dict]:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
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


async def gradebook_csv(db: AsyncSession, world: World) -> str:
    rows = await gradebook(db, world)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["email", "merchant", "participation",
                                             "mastery", "grade", "los_assessed", "los_total"])
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


async def mastery_heatmap(db: AsyncSession, world: World) -> dict:
    """LO × student grid for the instructor dashboard."""
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
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
        grid.append({
            "merchant": p.merchant_name,
            "scores": {lo.id: by_lo.get(lo.id) for lo in relevant},
        })
    return {
        "los": [{"id": lo.id, "text": lo.text, "week": lo.week} for lo in relevant],
        "students": grid,
    }

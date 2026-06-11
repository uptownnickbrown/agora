"""Moment detection (spec §10.2): a rules engine watching the simulation for
pedagogically interesting moments. Each detection becomes a Feed card with a
summary and a suggested instructor response.
"""
from __future__ import annotations

import statistics

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    Compact,
    CompactMember,
    DbTrade,
    DetectedMoment,
    Player,
    PriceSnapshot,
    World,
)
from .worlds import good_unlocked


async def run_detectors(db: AsyncSession, world: World) -> list[DetectedMoment]:
    moments: list[DetectedMoment] = []
    moments += await _price_moves(db, world)
    moments += await _concentration(db, world)
    moments += await _liquidity_and_shortage(db, world)
    moments += await _engagement(db, world)
    moments += await _commons(db, world)
    moments += await _cartel_signature(db, world)
    for m in moments:
        db.add(m)
    return moments


def _moment(world: World, kind: str, severity: str, summary: str, payload: dict | None = None):
    return DetectedMoment(world_id=world.id, world_day=world.world_day, kind=kind,
                          severity=severity, summary=summary, payload=payload or {})


async def _closes(db, world, good_id, n=8) -> list[int]:
    rows = (
        await db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.world_id == world.id,
                   PriceSnapshot.good_id == good_id,
                   PriceSnapshot.close.is_not(None))
            .order_by(PriceSnapshot.world_day.desc())
            .limit(n)
        )
    ).all()
    return [r.close for r in reversed(rows)]


async def _price_moves(db, world) -> list:
    out = []
    for good_id in T.GOODS:
        if not good_unlocked(world, good_id):
            continue
        closes = await _closes(db, world, good_id)
        if len(closes) < 4:
            continue
        *prev, today = closes
        mean = statistics.mean(prev)
        std = statistics.pstdev(prev) or 1
        z = (today - mean) / std
        jump = (today - mean) / mean if mean else 0
        if z > 2.5 or jump > 0.4:
            out.append(_moment(world, "price_spike", "notable",
                               f"{good_id} spiked to {today} (recent mean {mean:.0f}). "
                               f"Teachable: what shifted — supply or demand?",
                               {"good": good_id, "close": today, "z": round(z, 2)}))
        elif z < -2.5 or jump < -0.4:
            out.append(_moment(world, "price_crash", "notable",
                               f"{good_id} fell to {today} (recent mean {mean:.0f}). "
                               f"Glut, demand collapse, or entry?",
                               {"good": good_id, "close": today, "z": round(z, 2)}))
    return out


async def _concentration(db, world) -> list:
    out = []
    rows = (
        await db.execute(
            select(DbTrade.good_id, DbTrade.buyer_player_id, func.sum(DbTrade.qty))
            .where(DbTrade.world_id == world.id,
                   DbTrade.world_day >= world.world_day - 2)
            .group_by(DbTrade.good_id, DbTrade.buyer_player_id)
        )
    ).all()
    totals: dict[str, int] = {}
    for good_id, _, qty in rows:
        totals[good_id] = totals.get(good_id, 0) + qty
    for good_id, buyer_id, qty in rows:
        total = totals.get(good_id, 0)
        if total >= 20 and qty / total > 0.5:
            buyer = await db.get(Player, buyer_id)
            if buyer.is_npc:
                continue
            out.append(_moment(
                world, "market_concentration", "alert",
                f"{buyer.merchant_name} took {qty}/{total} of recent {good_id} buying "
                f"({qty / total:.0%}). A corner forming? Consider teaching monopoly early, "
                f"or an antitrust action.",
                {"good": good_id, "share": round(qty / total, 2),
                 "player_id": str(buyer_id)}))
    return out


async def _liquidity_and_shortage(db, world) -> list:
    out = []
    rows = (
        await db.scalars(
            select(PriceSnapshot).where(PriceSnapshot.world_id == world.id,
                                        PriceSnapshot.world_day == world.world_day)
        )
    ).all()
    ceilings = (world.market_rules or {}).get("ceilings") or {}
    for snap in rows:
        if snap.unfilled_demand > max(20, 3 * max(1, snap.volume)):
            controlled = snap.good_id in ceilings
            out.append(_moment(
                world, "shortage", "alert",
                f"Shortage in {snap.good_id}: {snap.unfilled_demand} units of demand went "
                f"unfilled vs volume {snap.volume}."
                + (" A price ceiling is active — shelves are empty and a gray market is"
                   " likely. This is the Week 3 lesson happening." if controlled else ""),
                {"good": snap.good_id, "unfilled": snap.unfilled_demand,
                 "volume": snap.volume, "ceiling_active": controlled}))
        if snap.suppressed_asks > 10 and snap.good_id in ceilings:
            out.append(_moment(
                world, "seller_withdrawal", "notable",
                f"Sellers withdrew {snap.suppressed_asks} {snap.good_id} asks above the "
                f"legal price — withholding in action.",
                {"good": snap.good_id, "suppressed": snap.suppressed_asks}))
    return out


async def _engagement(db, world) -> list:
    out = []
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    missing = [p for p in players if world.world_day - p.last_active_day >= 5]
    if missing:
        names = ", ".join(p.merchant_name for p in missing[:5])
        out.append(_moment(world, "disengagement", "info",
                           f"{len(missing)} student(s) inactive 5+ days: {names}"
                           + ("…" if len(missing) > 5 else ""),
                           {"count": len(missing)}))
    return out


async def _commons(db, world) -> list:
    out = []
    if world.current_week >= 6:
        cap = T.BALANCE["fish_capacity"]
        ratio = world.fish_stock / cap
        if ratio < 0.1:
            out.append(_moment(world, "fishery_collapse", "alert",
                               f"The fishery has collapsed ({world.fish_stock}/{cap}). "
                               f"Tragedy of the commons, live. Quota or closed season?",
                               {"stock": world.fish_stock}))
        elif ratio < 0.3:
            out.append(_moment(world, "fishery_depletion", "notable",
                               f"Fish stock at {ratio:.0%} of capacity and falling.",
                               {"stock": world.fish_stock}))
        if world.smog > T.BALANCE["smog_efficiency_threshold"]:
            out.append(_moment(world, "smog_threshold", "notable",
                               f"District smog at {world.smog} — facility efficiency is "
                               f"degrading for everyone. Pigouvian moment.",
                               {"smog": world.smog}))
    return out


async def _cartel_signature(db, world) -> list:
    out = []
    if world.current_week < 7:
        return out
    compacts = (
        await db.scalars(
            select(Compact).where(Compact.world_id == world.id,
                                  Compact.kind == "price_accord",
                                  Compact.dissolved_day.is_(None))
        )
    ).all()
    for compact in compacts:
        member_ids = [
            m.player_id
            for m in (
                await db.scalars(
                    select(CompactMember).where(CompactMember.compact_id == compact.id,
                                                CompactMember.left_day.is_(None))
                )
            ).all()
        ]
        if len(member_ids) < 2:
            continue
        good = (compact.terms or {}).get("good")
        if not good:
            continue
        sells = (
            await db.scalars(
                select(DbTrade).where(DbTrade.world_id == world.id,
                                      DbTrade.good_id == good,
                                      DbTrade.world_day == world.world_day,
                                      DbTrade.seller_player_id.in_(member_ids))
            )
        ).all()
        if len(sells) >= 3:
            prices = [t.price for t in sells]
            spread = (max(prices) - min(prices)) / max(prices)
            if spread < 0.03:
                out.append(_moment(
                    world, "cartel_parallel_pricing", "alert",
                    f"Compact '{compact.name}' members sold {good} at near-identical "
                    f"prices ({min(prices)}–{max(prices)}). Cartel discipline holding — "
                    f"for now. Watch for defection; it makes a great lecture.",
                    {"compact": str(compact.id), "good": good}))
    return out

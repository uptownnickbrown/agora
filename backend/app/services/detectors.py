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


def _cap(good_id: str) -> str:
    return good_id.capitalize()


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
                               f"{_cap(good_id)} spiked to {today}, up from a recent "
                               f"average of {mean:.0f}. Worth asking the class whether "
                               f"supply shifted or demand did.",
                               {"good": good_id, "close": today, "z": round(z, 2)}))
        elif z < -2.5 or jump < -0.4:
            out.append(_moment(world, "price_crash", "notable",
                               f"{_cap(good_id)} fell to {today}, down from a recent "
                               f"average of {mean:.0f}. A glut, fading demand, and new "
                               f"sellers entering are all candidate stories.",
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
                f"{buyer.merchant_name} bought {qty} of the last {total} units of "
                f"{good_id} traded ({qty / total:.0%}). If a corner is forming, this is "
                f"an early chance to teach monopoly, or to bring an antitrust action.",
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
                f"{_cap(snap.good_id)} is running short: {snap.unfilled_demand} units of "
                f"demand went unfilled against a traded volume of {snap.volume}."
                + (" With the price ceiling in force, empty shelves and a gray market "
                   "are the textbook prediction, and your students are living it."
                   if controlled else ""),
                {"good": snap.good_id, "unfilled": snap.unfilled_demand,
                 "volume": snap.volume, "ceiling_active": controlled}))
        if snap.suppressed_asks > 10 and snap.good_id in ceilings:
            out.append(_moment(
                world, "seller_withdrawal", "notable",
                f"Sellers pulled {snap.suppressed_asks} {snap.good_id} asks rather than "
                f"sell at the legal maximum. That is withholding, just as the model "
                f"predicts.",
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
        if len(missing) > 5:
            names += f", and {len(missing) - 5} more"
        noun = "student has" if len(missing) == 1 else "students have"
        out.append(_moment(world, "disengagement", "info",
                           f"{len(missing)} {noun} been inactive for five days or "
                           f"more: {names}.",
                           {"count": len(missing)}))
    return out


async def _commons(db, world) -> list:
    out = []
    if world.current_week >= 6:
        from .fun import fish_capacity

        cap = fish_capacity(world)
        ratio = world.fish_stock / cap
        if ratio < 0.1:
            out.append(_moment(world, "fishery_collapse", "alert",
                               f"The fishery has collapsed, with stock at "
                               f"{world.fish_stock} of a possible {cap}. The tragedy of "
                               f"the commons is playing out live; a quota or a closed "
                               f"season are the standard remedies.",
                               {"stock": world.fish_stock}))
        elif ratio < 0.3:
            out.append(_moment(world, "fishery_depletion", "notable",
                               f"Fish stock is down to {ratio:.0%} of capacity and "
                               f"still falling.",
                               {"stock": world.fish_stock}))
        if world.smog > T.BALANCE["smog_efficiency_threshold"]:
            out.append(_moment(world, "smog_threshold", "notable",
                               f"District smog has reached {world.smog}, and facility "
                               f"efficiency is degrading for everyone. A textbook "
                               f"opening for a Pigouvian tax.",
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
            # Cluster member sale prices: a cartel shows up as a pile of prints
            # at one identical price (the accord), even amid market noise.
            buckets: dict[int, list] = {}
            for t in sells:
                buckets.setdefault(t.price, []).append(t)
            price, cluster = max(buckets.items(), key=lambda kv: len(kv[1]))
            sellers = {t.seller_player_id for t in cluster}
            if len(cluster) >= 3 and len(sellers) >= 2:
                out.append(_moment(
                    world, "cartel_parallel_pricing", "alert",
                    f"Members of the compact '{compact.name}' made {len(cluster)} "
                    f"{good} sales at an identical {price} coppers. The accord is "
                    f"holding for now; watch for defection, which makes a great "
                    f"lecture when it comes.",
                    {"compact": str(compact.id), "good": good, "price": price}))
    return out

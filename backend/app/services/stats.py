"""Analytics projections: net worth, Gini, participation, leaderboards."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    EconEvent,
    FishingCatch,
    Inventory,
    Player,
    PlayerDayStat,
    Streak,
    Team,
    World,
    WorldDayStat,
)
from .market import last_close

PARTICIPATION_KINDS = {
    "order_placed", "trade", "gathered", "crafted", "shop_listed", "fishing_cast",
    "puzzle_solved", "puzzle_failed", "merchant_completed", "facility_built",
    "facility_upgraded", "check_answered", "tutor_chat", "license_bid",
    "compact_created", "compact_joined",
}
PARTICIPATION_DAILY_CAP = 12  # diminishing returns on raw action spam


async def net_worth(db: AsyncSession, world: World, player: Player,
                    price_cache: dict[str, int] | None = None) -> int:
    total = player.coins
    invs = (
        await db.scalars(
            select(Inventory).where(Inventory.world_id == world.id,
                                    Inventory.player_id == player.id)
        )
    ).all()
    for inv in invs:
        if inv.qty <= 0:
            continue
        if price_cache is not None and inv.good_id in price_cache:
            price = price_cache[inv.good_id]
        else:
            price = await last_close(db, world, inv.good_id) or T.GOODS[inv.good_id].anchor
            if price_cache is not None:
                price_cache[inv.good_id] = price
        total += inv.qty * price
    return total


def gini_bp(values: list[int]) -> int:
    vals = sorted(max(0, v) for v in values)
    n = len(vals)
    s = sum(vals)
    if n == 0 or s == 0:
        return 0
    cum = 0
    weighted = 0
    for i, v in enumerate(vals, start=1):
        weighted += i * v
        cum += v
    g = (2 * weighted) / (n * s) - (n + 1) / n
    return round(g * 10_000)


async def record_day_stats(db: AsyncSession, world: World) -> dict:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    # participation points today: distinct meaningful actions, capped
    rows = (
        await db.execute(
            select(EconEvent.actor_player_id, EconEvent.kind, func.count())
            .where(EconEvent.world_id == world.id,
                   EconEvent.world_day == world.world_day,
                   EconEvent.actor_player_id.is_not(None),
                   EconEvent.kind.in_(PARTICIPATION_KINDS))
            .group_by(EconEvent.actor_player_id, EconEvent.kind)
        )
    ).all()
    points: dict[uuid.UUID, int] = {}
    for actor_id, kind, count in rows:
        points[actor_id] = points.get(actor_id, 0) + min(3, count)  # diminishing per kind

    price_cache: dict[str, int] = {}
    worths = []
    active = 0
    for p in players:
        worth = await net_worth(db, world, p, price_cache)
        worths.append(worth)
        pts = min(PARTICIPATION_DAILY_CAP, points.get(p.id, 0))
        if p.last_active_day == world.world_day:
            active += 1
        db.add(PlayerDayStat(world_id=world.id, player_id=p.id, world_day=world.world_day,
                             coins=p.coins, net_worth=worth, participation=pts))
    from ..models import DbTrade

    volume = await db.scalar(
        select(func.coalesce(func.sum(DbTrade.qty), 0)).where(
            DbTrade.world_id == world.id, DbTrade.world_day == world.world_day)
    )
    db.add(WorldDayStat(world_id=world.id, world_day=world.world_day,
                        gini_bp=gini_bp(worths), total_volume=volume or 0,
                        active_players=active, smog=world.smog,
                        fish_stock=world.fish_stock))
    return {"gini_bp": gini_bp(worths), "volume": volume, "active": active}


async def leaderboards(db: AsyncSession, world: World) -> dict:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    price_cache: dict[str, int] = {}
    wealth = []
    for p in players:
        wealth.append({"merchant": p.merchant_name,
                       "net_worth": await net_worth(db, world, p, price_cache)})
    wealth.sort(key=lambda r: -r["net_worth"])

    streak_rows = (
        await db.scalars(select(Streak).where(Streak.world_id == world.id,
                                              Streak.kind == "puzzle"))
    ).all()
    streaks = []
    for s in streak_rows:
        p = await db.get(Player, s.player_id)
        streaks.append({"merchant": p.merchant_name, "streak": s.count, "best": s.best})
    streaks.sort(key=lambda r: -r["streak"])

    catch = (
        await db.execute(
            select(FishingCatch.player_id, func.max(FishingCatch.weight))
            .where(FishingCatch.world_id == world.id)
            .group_by(FishingCatch.player_id)
        )
    ).all()
    anglers = []
    for pid, weight in catch:
        p = await db.get(Player, pid)
        anglers.append({"merchant": p.merchant_name, "weight": weight})
    anglers.sort(key=lambda r: -r["weight"])

    teams = (await db.scalars(select(Team).where(Team.world_id == world.id))).all()
    houses = []
    for t in teams:
        members = [p for p in players if p.team_id == t.id]
        total = 0
        for m in members:
            total += await net_worth(db, world, m, price_cache)
        houses.append({"house": t.name, "net_worth": total, "members": len(members)})
    houses.sort(key=lambda r: -r["net_worth"])

    return {"wealth": wealth[:20], "puzzle_streaks": streaks[:10],
            "biggest_catch": anglers[:10], "houses": houses}

"""The Daily Market Close — the world's heartbeat (spec §12.2).

Order: scheduled beats fire -> orders expire -> official prices snapshot ->
facilities produce -> shops sell -> commons step -> effort regen -> loans ->
achievements -> detectors -> stats -> the Crier writes it all up -> next day.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    CrierPost,
    DbTrade,
    FishingCatch,
    GuildLoan,
    Player,
    PlayerAchievement,
    PriceSnapshot,
    ScheduledEvent,
    Streak,
    World,
)
from . import interventions
from .common import adjust_coins, emit
from .detectors import run_detectors
from .fun import award, fishery_regen
from .licenses import close_auction
from .market import expire_orders, snapshot_day
from .npc import refresh_npc_orders
from .production import regen_effort, run_daily_production
from .shops import run_retail_demand
from .stats import record_day_stats
from .worlds import advance_week


async def run_daily_close(db: AsyncSession, world: World) -> dict:
    report: dict = {"world_day": world.world_day}

    await _fire_scheduled(db, world)
    unfilled = await expire_orders(db, world)
    await snapshot_day(db, world, unfilled)
    production = await run_daily_production(db, world)
    retail = await run_retail_demand(db, world)
    if world.current_week >= 1:
        fishery_regen(world)
    await regen_effort(db, world)
    await _accrue_loans(db, world)
    await _achievement_sweep(db, world)
    moments = await run_detectors(db, world)
    day_stats = await record_day_stats(db, world)
    await _write_market_report(db, world, day_stats)

    report.update({"produced": production["produced"], "retail_sold": retail,
                   "moments": len(moments), **day_stats})

    world.world_day += 1
    if (world.config or {}).get("pacing") == "calendar" and world.world_day % T.DAYS_PER_WEEK == 0:
        if world.current_week < 7:
            await advance_week(db, world)

    # Tomorrow's NPC flow posts at the open of the new day.
    await refresh_npc_orders(db, world)
    await emit(db, world, "daily_close", {"day": report["world_day"]})
    return report


async def _fire_scheduled(db: AsyncSession, world: World) -> None:
    due = (
        await db.scalars(
            select(ScheduledEvent).where(
                ScheduledEvent.world_id == world.id,
                ScheduledEvent.world_day <= world.world_day,
                ~ScheduledEvent.executed,
            ).order_by(ScheduledEvent.world_day)
        )
    ).all()
    for ev in due:
        ev.executed = True
        params = ev.params or {}
        headline = params.pop("headline", None)
        if ev.kind == "announce":
            db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="news",
                             title=params.get("title", "News"),
                             body=params.get("body", "")))
        elif ev.kind == "license_auction_open":
            await interventions.execute(db, world, "license_auction", {
                "good": params["good"], "auction_id": params["auction_id"],
                "licenses": params["licenses"],
                "close_day_offset": params.get("close_day_offset", 2),
            }, headline=headline)
        elif ev.kind == "license_auction_close":
            winners = await close_auction(db, world, params["good"],
                                          params["auction_id"], params["licenses"])
            names = ", ".join(w["merchant"] for w in winners) or "no one (no valid bids!)"
            db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="news",
                             title=f"The {params['good']} licenses are awarded!",
                             body=f"By sealed bid, the Crown licenses: {names}."))
            for w in winners:
                pass
        elif ev.kind == "tournament_start":
            world.state = "tournament"
            db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="event",
                             title=headline or "The Market Wars begin!",
                             body="Four days. Every system. House against house."))
            await emit(db, world, "tournament_start", {})
        elif ev.kind == "tournament_end":
            from .stats import leaderboards

            boards = await leaderboards(db, world)
            houses = boards["houses"]
            champion = houses[0]["house"] if houses else "nobody"
            world.state = "active"
            db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="event",
                             title=f"The Market Wars conclude — {champion} triumphant!",
                             body="\n".join(f"{h['house']}: {h['net_worth']} coppers"
                                            for h in houses)))
            await emit(db, world, "tournament_end", {"champion": champion})
        else:
            # interventions catalog kinds (supply_shock, price_ceiling, ...)
            kind = {"repeal_ceiling": "repeal_ceiling"}.get(ev.kind, ev.kind)
            await interventions.execute(db, world, kind, params, headline=headline)


async def _accrue_loans(db: AsyncSession, world: World) -> None:
    loans = (
        await db.scalars(
            select(GuildLoan).where(GuildLoan.world_id == world.id, GuildLoan.outstanding > 0)
        )
    ).all()
    for loan in loans:
        interest = max(1, loan.outstanding * loan.rate_bp_per_day // 10_000)
        loan.outstanding += interest
        player = await db.get(Player, loan.player_id)
        # gentle auto-repay: 20% of coins above a cushion
        cushion = 60
        if player.coins > cushion:
            payment = min(loan.outstanding, (player.coins - cushion) // 5)
            if payment > 0:
                adjust_coins(player, -payment)
                loan.outstanding -= payment


async def _achievement_sweep(db: AsyncSession, world: World) -> None:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    ceilings = (world.market_rules or {}).get("ceilings") or {}
    for p in players:
        total_fish = await db.scalar(
            select(func.coalesce(func.sum(FishingCatch.fish_qty), 0)).where(
                FishingCatch.player_id == p.id)
        )
        if total_fish >= 50:
            await award(db, world, p, "master_angler")
        traded = await db.scalar(
            select(func.count()).select_from(DbTrade).where(
                (DbTrade.buyer_player_id == p.id) | (DbTrade.seller_player_id == p.id))
        )
        if traded:
            await award(db, world, p, "first_trade")
        streak = await db.scalar(
            select(Streak).where(Streak.player_id == p.id, Streak.kind == "puzzle")
        )
        if streak is not None and streak.best >= 7:
            await award(db, world, p, "puzzle_week")
        # Arbitrage Artist: bought below and sold above in the same good today
        buys = (
            await db.execute(
                select(DbTrade.good_id, func.min(DbTrade.price)).where(
                    DbTrade.buyer_player_id == p.id,
                    DbTrade.world_day == world.world_day).group_by(DbTrade.good_id)
            )
        ).all()
        sell_max = dict((
            await db.execute(
                select(DbTrade.good_id, func.max(DbTrade.price)).where(
                    DbTrade.seller_player_id == p.id,
                    DbTrade.world_day == world.world_day).group_by(DbTrade.good_id)
            )
        ).all())
        for good_id, min_buy in buys:
            if good_id in sell_max and sell_max[good_id] > min_buy * 1.2:
                await award(db, world, p, "arbitrage_artist")
        if "bread" in ceilings:
            from .common import get_inventory

            inv = await get_inventory(db, world.id, p.id, "bread")
            if inv.qty > 0:
                await award(db, world, p, "survived_drought")


async def _write_market_report(db: AsyncSession, world: World, day_stats: dict) -> None:
    snaps = (
        await db.scalars(
            select(PriceSnapshot).where(PriceSnapshot.world_id == world.id,
                                        PriceSnapshot.world_day == world.world_day)
        )
    ).all()
    lines = []
    movers: list[tuple[str, int, int]] = []
    for s in snaps:
        if s.close is None:
            continue
        prev = await db.scalar(
            select(PriceSnapshot.close).where(
                PriceSnapshot.world_id == world.id, PriceSnapshot.good_id == s.good_id,
                PriceSnapshot.world_day < world.world_day,
                PriceSnapshot.close.is_not(None),
            ).order_by(PriceSnapshot.world_day.desc()).limit(1)
        )
        if prev:
            movers.append((s.good_id, s.close, s.close - prev))
        lines.append(f"{T.GOODS[s.good_id].name}: {s.close} coppers"
                     f" (vol {s.volume})")
    movers.sort(key=lambda m: -abs(m[2]))
    headline = "The markets hold steady."
    if movers and movers[0][2] != 0:
        g, close, delta = movers[0]
        verb = "soars" if delta > 0 else "tumbles"
        headline = f"{T.GOODS[g].name} {verb} to {close}!"

    # Named big movers — the Crier names names (DECISIONS.md #11).
    rows = (
        await db.execute(
            select(DbTrade.good_id, DbTrade.buyer_player_id, func.sum(DbTrade.qty))
            .where(DbTrade.world_id == world.id, DbTrade.world_day == world.world_day)
            .group_by(DbTrade.good_id, DbTrade.buyer_player_id)
        )
    ).all()
    totals: dict[str, int] = {}
    for good_id, _, qty in rows:
        totals[good_id] = totals.get(good_id, 0) + qty
    gossip = []
    for good_id, buyer_id, qty in rows:
        if totals[good_id] >= 12 and qty / totals[good_id] > 0.5:
            buyer = await db.get(Player, buyer_id)
            if not buyer.is_npc:
                gossip.append(f"{buyer.merchant_name} took {qty / totals[good_id]:.0%} of "
                              f"today's {T.GOODS[good_id].name} buying. Interesting.")
    body = "\n".join(lines)
    if gossip:
        body += "\n\nHEARD IN THE SQUARE:\n" + "\n".join(gossip)
    db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="market_report",
                     title=f"Day {world.world_day} Market Close: {headline}", body=body))

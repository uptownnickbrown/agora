"""Epilogue: "Your Economic Story" — per-student recap (spec §6 wk7).
Shareable, delightful, and a study artifact.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    CheckAttempt,
    DbTrade,
    FishingCatch,
    MasteryEstimate,
    Player,
    PlayerAchievement,
    PlayerDayStat,
    Streak,
    World,
)
from ..services.fun import achievement_name
from .bank import LEARNING_OBJECTIVES


async def your_economic_story(db: AsyncSession, world: World, player: Player) -> dict:
    day_stats = (
        await db.scalars(
            select(PlayerDayStat)
            .where(PlayerDayStat.world_id == world.id,
                   PlayerDayStat.player_id == player.id)
            .order_by(PlayerDayStat.world_day)
        )
    ).all()
    worth_curve = [{"day": s.world_day, "net_worth": s.net_worth} for s in day_stats]

    sells = (
        await db.scalars(
            select(DbTrade).where(DbTrade.world_id == world.id,
                                  DbTrade.seller_player_id == player.id)
        )
    ).all()
    buys = (
        await db.scalars(
            select(DbTrade).where(DbTrade.world_id == world.id,
                                  DbTrade.buyer_player_id == player.id)
        )
    ).all()
    best_trade = None
    min_buy: dict[str, int] = {}
    for t in buys:
        min_buy[t.good_id] = min(min_buy.get(t.good_id, 10**9), t.price)
    for t in sells:
        if t.good_id in min_buy and t.price > min_buy[t.good_id]:
            gain = (t.price - min_buy[t.good_id]) * t.qty
            if best_trade is None or gain > best_trade["gain"]:
                best_trade = {"good": T.GOODS[t.good_id].name, "bought_at": min_buy[t.good_id],
                              "sold_at": t.price, "qty": t.qty, "gain": gain}

    total_fish = await db.scalar(
        select(func.coalesce(func.sum(FishingCatch.fish_qty), 0)).where(
            FishingCatch.player_id == player.id)
    )
    achievements = (
        await db.scalars(
            select(PlayerAchievement).where(PlayerAchievement.player_id == player.id)
        )
    ).all()
    streaks = (
        await db.scalars(select(Streak).where(Streak.player_id == player.id))
    ).all()
    mastery = (
        await db.scalars(
            select(MasteryEstimate).where(MasteryEstimate.world_id == world.id,
                                          MasteryEstimate.player_id == player.id)
        )
    ).all()
    checks = await db.scalar(
        select(func.count()).select_from(CheckAttempt).where(
            CheckAttempt.player_id == player.id)
    )
    strongest = sorted(mastery, key=lambda m: -m.score)[:3]
    growth = sorted(mastery, key=lambda m: -m.attempts)[:3]

    chapters = []
    if worth_curve:
        peak = max(worth_curve, key=lambda w: w["net_worth"])
        trough = min(worth_curve, key=lambda w: w["net_worth"])
        chapters.append(f"You started with {T.BALANCE['starting_coins']} coppers and a "
                        f"sack of {player.aptitude_good or 'goods'}. At your height "
                        f"(day {peak['day']}) you were worth {peak['net_worth']} coppers.")
        if trough["net_worth"] < T.BALANCE["starting_coins"]:
            chapters.append(f"Day {trough['day']} was the dark one — down to "
                            f"{trough['net_worth']}. You climbed back. That's the part "
                            f"worth remembering.")
    if best_trade:
        chapters.append(f"Your finest trade: {best_trade['good']} bought at "
                        f"{best_trade['bought_at']}, sold at {best_trade['sold_at']} — "
                        f"a {best_trade['gain']}-copper swing. Buy low. Sell high. "
                        f"You actually did it.")
    if total_fish:
        chapters.append(f"You pulled {total_fish} fish from the commons. "
                        f"You know how that story ended.")

    return {
        "merchant": player.merchant_name,
        "world_days": world.world_day,
        "net_worth_curve": worth_curve,
        "best_trade": best_trade,
        "chapters": chapters,
        "achievements": [
            {"id": a.achievement_id,
             "name": achievement_name(a.achievement_id),
             "trophy": a.achievement_id.startswith("trophy:"),
             "day": a.world_day}
            for a in achievements
        ],
        "streaks": [{"kind": s.kind, "best": s.best} for s in streaks],
        "checks_completed": checks,
        "mastery_strongest": [
            {"lo": LEARNING_OBJECTIVES[m.lo_id].text, "pct": round(m.score / 10)}
            for m in strongest if m.lo_id in LEARNING_OBJECTIVES
        ],
        "mastery_most_practiced": [
            {"lo": LEARNING_OBJECTIVES[m.lo_id].text, "attempts": m.attempts}
            for m in growth if m.lo_id in LEARNING_OBJECTIVES
        ],
    }

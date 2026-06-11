"""NPC liquidity: turns NPCSchedule rows into daily order flow.

Schedules are discrete piecewise-linear curves (same construction the harness
validated). Interventions mutate price_mult/qty_mult, optionally with an
auto-revert day. Posted via the normal market path so NPC flow obeys price
controls, taxes, and matching like everyone else.
"""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import NPCSchedule, Player, World
from .market import place_order
from .worlds import good_unlocked

ORDERS_PER_SCHEDULE = 6


async def refresh_npc_orders(db: AsyncSession, world: World, rng: random.Random | None = None) -> int:
    """Post the day's NPC flow. Returns number of orders submitted."""
    rng = rng or random.Random(f"{world.id}:{world.world_day}")
    schedules = (
        await db.scalars(select(NPCSchedule).where(NPCSchedule.world_id == world.id))
    ).all()
    posted = 0
    for sched in schedules:
        if sched.revert_day is not None and world.world_day >= sched.revert_day:
            sched.price_mult = 1.0
            sched.qty_mult = 1.0
            sched.revert_day = None
        if sched.paused or not good_unlocked(world, sched.good_id):
            continue
        total_qty = max(0, round(sched.qty_per_day * sched.qty_mult))
        if total_qty == 0:
            continue
        npc = await db.get(Player, sched.npc_player_id)
        n_orders = min(ORDERS_PER_SCHEDULE, total_qty)
        base, extra = divmod(total_qty, n_orders)
        for i in range(n_orders):
            qty = base + (1 if i < extra else 0)
            frac = (i + rng.random()) / n_orders
            p = sched.p_low + frac * (sched.p_high - sched.p_low)
            price = max(1, round(p * sched.price_mult))
            await place_order(
                db, world, npc, sched.good_id, sched.side, qty, price, ttl_days=1
            )
            posted += 1
    return posted


async def shift_schedule(
    db: AsyncSession,
    world: World,
    good_id: str,
    side: str,
    price_mult: float | None = None,
    qty_mult: float | None = None,
    revert_after_days: int | None = None,
) -> None:
    sched = await db.scalar(
        select(NPCSchedule).where(
            NPCSchedule.world_id == world.id,
            NPCSchedule.good_id == good_id,
            NPCSchedule.side == side,
        )
    )
    if sched is None:
        return
    if price_mult is not None:
        sched.price_mult = price_mult
    if qty_mult is not None:
        sched.qty_mult = qty_mult
    sched.revert_day = (
        world.world_day + revert_after_days if revert_after_days is not None else None
    )

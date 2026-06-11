"""ARQ worker: per-World scheduled jobs (spec §12.2 tick model).

- daily_market_close: the world heartbeat (close.run_daily_close).
- fast_tick (~5 min): NPC order refresh between closes.

Cron wiring runs every active world hourly and closes those whose local
midnight has passed; v1 keeps it simple with world-local day length = real day.
"""
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from .config import get_settings
from .db import make_engine, make_session_factory
from .models import World
from .services.close import run_daily_close
from .services.npc import refresh_npc_orders

_factory = None


def _session_factory():
    global _factory
    if _factory is None:
        _factory = make_session_factory(make_engine())
    return _factory


async def daily_market_close(ctx: dict) -> int:
    closed = 0
    async with _session_factory()() as db:
        async with db.begin():
            worlds = (
                await db.scalars(
                    select(World).where(World.state.in_(["onboarding", "active", "tournament"]))
                )
            ).all()
            for world in worlds:
                await run_daily_close(db, world)
                closed += 1
    return closed


async def fast_tick(ctx: dict) -> int:
    posted = 0
    async with _session_factory()() as db:
        async with db.begin():
            worlds = (
                await db.scalars(
                    select(World).where(World.state.in_(["onboarding", "active", "tournament"]))
                )
            ).all()
            for world in worlds:
                posted += await refresh_npc_orders(db, world)
    return posted


class WorkerSettings:
    functions = [daily_market_close, fast_tick]
    cron_jobs = [
        cron(daily_market_close, hour={4}, minute={59}),  # 11:59pm ET ~= 04:59 UTC
        cron(fast_tick, minute=set(range(0, 60, 5))),
    ]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

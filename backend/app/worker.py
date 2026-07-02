"""ARQ worker: per-World scheduled jobs (spec §12.2 tick model).

- daily_market_close: the world heartbeat (close.run_daily_close).
- fast_tick (~5 min): NPC order refresh between closes.

Cron wiring runs every active world hourly and closes those whose local
midnight has passed; v1 keeps it simple with world-local day length = real day.
"""
from datetime import date

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


async def _live_world_ids(factory) -> list:
    async with factory() as db:
        return list(
            await db.scalars(
                select(World.id).where(
                    World.state.in_(["onboarding", "active", "tournament"]))
            )
        )


async def daily_market_close(ctx: dict) -> int:
    """One transaction per world: a bad world must not roll back everyone
    else's day, and a crash mid-run must not lose completed closes."""
    import logging

    factory = _session_factory()
    today = date.today().isoformat()
    closed = 0
    for wid in await _live_world_ids(factory):
        try:
            async with factory() as db:
                async with db.begin():
                    world = await db.get(World, wid, with_for_update=True)
                    if world is None or world.state not in (
                            "onboarding", "active", "tournament"):
                        continue
                    # Idempotent per real day: an instructor's manual close
                    # already advanced this world today.
                    if (world.config or {}).get("last_close_date") == today:
                        continue
                    await run_daily_close(db, world)
                    closed += 1
        except Exception:  # noqa: BLE001 - isolate per-world failures
            logging.getLogger("agora.worker").exception(
                "daily close failed for world %s", wid)
    return closed


async def email_sweep(ctx: dict) -> int:
    """Send due instructor digests (stamped by advance_week). Build + send
    happen outside the close transaction; the sweep is idempotent."""
    from .services.digest import process_due_digests

    return await process_due_digests(_session_factory())


async def demo_reset(ctx: dict) -> int:
    """Nightly demo rotation: retire the shared demo world (god-mode guests
    leave ceilings and droughts behind) and seed a fresh mid-course one, so
    the landing-page demo is always at its best. Requires tests/ + scripts/
    in the image (see Dockerfile). No-op unless the demo is enabled here."""
    import logging
    import time
    from datetime import datetime, timedelta, timezone

    settings = get_settings()
    if settings.env not in ("dev", "test") and not settings.demo_enabled:
        return 0
    factory = _session_factory()
    async with factory() as db:
        async with db.begin():
            worlds = (await db.scalars(select(World))).all()
            demos = [w for w in worlds if (w.config or {}).get("is_demo")]
            fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=20)
            if any(w.created_at and w.created_at >= fresh_cutoff for w in demos):
                return 0  # already rotated today (restart storm guard)
            for w in demos:
                w.config = {**w.config, "is_demo": False}
                w.state = "epilogue"  # retire: stops close/tick attention
    try:
        from scripts.seed_midcourse import main as seed_main

        await seed_main(25, f"demo{time.strftime('%m%d%H%M')}", demo=True)
        return 1
    except Exception:  # noqa: BLE001
        logging.getLogger("agora.worker").exception("demo reset failed")
        return 0


async def fast_tick(ctx: dict) -> int:
    import logging

    factory = _session_factory()
    posted = 0
    for wid in await _live_world_ids(factory):
        try:
            async with factory() as db:
                async with db.begin():
                    world = await db.get(World, wid)
                    if world is not None:
                        posted += await refresh_npc_orders(db, world)
        except Exception:  # noqa: BLE001
            logging.getLogger("agora.worker").exception(
                "fast tick failed for world %s", wid)
    return posted


class WorkerSettings:
    functions = [daily_market_close, fast_tick, email_sweep, demo_reset]
    cron_jobs = [
        cron(daily_market_close, hour={4}, minute={59}),  # 11:59pm ET ~= 04:59 UTC
        cron(fast_tick, minute=set(range(0, 60, 5))),
        # Every 10 min: digests land within minutes of a week boundary,
        # whether the close cron or a manual advance crossed it.
        cron(email_sweep, minute={9, 19, 29, 39, 49, 59}),
        # After the nightly closes: retire yesterday's demo world, seed a
        # fresh one (a ~1 min simulation through the real service layer).
        cron(demo_reset, hour={5}, minute={30}),
    ]
    job_timeout = 900  # the demo reseed simulates 25 days; give it room
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

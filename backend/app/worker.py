"""ARQ worker: per-World scheduled jobs (spec §12.2 tick model).

- daily_market_close: the world heartbeat (close.run_daily_close).
- fast_tick (~5 min): NPC order refresh between closes.

Cron wiring runs every active world hourly and closes those whose local
midnight has passed; v1 keeps it simple with world-local day length = real day.
"""
import os
import sys
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


def _ensure_seeder_importable() -> None:
    """demo_reset seeds via scripts/seed_midcourse.py, which imports tests/bots.py.
    Neither `scripts` nor `tests` is installed as a package (pyproject ships only
    `app*`/`sim*`), so when the worker runs from an installed copy — `arq
    app.worker.WorkerSettings` resolves `app` out of site-packages, NOT the
    source tree — `from scripts…` raises ImportError. That import lived inside a
    caught try, so the nightly demo rotation failed silently in prod for days.

    Put the project root (the dir holding scripts/ AND tests/) on sys.path.
    First candidate is the working directory (the Dockerfile's WORKDIR /srv in
    prod, backend/ under pytest); __file__-relative candidates cover odd cwds."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.getcwd(), os.path.dirname(here),
                  os.path.dirname(os.path.dirname(here))]
    for root in candidates:
        if (os.path.isdir(os.path.join(root, "scripts"))
                and os.path.isdir(os.path.join(root, "tests"))):
            if root not in sys.path:
                sys.path.insert(0, root)
            return


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


async def demo_reset(ctx: dict, force: bool = False) -> int:
    """Nightly demo rotation, blue-green: seed a fresh mid-course world as an
    unflagged CANDIDATE first, and only after the seed fully succeeds flip the
    is_demo flag to it (one short transaction) while retiring the old world.
    A seed that dies mid-run therefore never touches the live demo — the old
    world keeps serving, and the next scheduled run retries.

    Requires tests/ + scripts/ in the image (see Dockerfile). No-op unless
    the demo is enabled here. `force=True` (manual runs) skips the freshness
    guard."""
    import logging
    import time
    from datetime import datetime, timedelta, timezone

    log = logging.getLogger("agora.worker")
    settings = get_settings()
    if settings.env not in ("dev", "test") and not settings.demo_enabled:
        return 0
    factory = _session_factory()
    now = datetime.now(timezone.utc)

    def aware(dt):  # sqlite hands back naive datetimes; treat them as UTC
        return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    async with factory() as db:
        worlds = (await db.scalars(select(World))).all()
        flagged = [w.id for w in worlds if (w.config or {}).get("is_demo")]
        # Guard keys on the LIVE demo world's age: a fresh one means we
        # already rotated today; a failed seed never advances the clock, so
        # the next scheduled run naturally becomes the retry.
        fresh_cutoff = now - timedelta(hours=20)
        if not force and any(
                w.created_at and aware(w.created_at) >= fresh_cutoff
                for w in worlds if w.id in flagged):
            return 0

    try:
        _ensure_seeder_importable()
        from scripts.seed_midcourse import main as seed_main

        new_id = await seed_main(25, f"demo{time.strftime('%m%d%H%M%S')}",
                                 demo=False, candidate=True)
    except Exception:  # noqa: BLE001
        log.exception("demo seed failed — keeping the current demo world live")
        return 0

    # The switchover: short, atomic, and only reachable on a complete seed.
    async with factory() as db:
        async with db.begin():
            worlds = (await db.scalars(select(World))).all()
            for w in worlds:
                config = w.config or {}
                if w.id == new_id:
                    w.config = {**config, "is_demo": True,
                                "demo_candidate": False}
                elif config.get("is_demo"):
                    w.config = {**config, "is_demo": False}
                    w.state = "epilogue"  # retire: stops close/tick attention
                elif (config.get("demo_candidate")
                      and w.created_at
                      and aware(w.created_at) < now - timedelta(hours=20)):
                    # leftovers from failed seeds: quietly retire
                    w.state = "epilogue"
    log.info("demo rotation complete: world %s is live", new_id)
    return 1


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
        # After the nightly closes: seed a fresh demo world and flip to it.
        # Scheduled twice — the freshness guard makes the second run a no-op
        # when the first succeeded, and an automatic retry when it didn't.
        cron(demo_reset, hour={5}, minute={30}),
        cron(demo_reset, hour={6}, minute={45}),
    ]
    job_timeout = 900  # the demo reseed simulates 25 days; give it room
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

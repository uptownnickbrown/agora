"""ARQ worker: per-World scheduled jobs (spec §12.2 tick model).

- daily_market_close: production payout, upkeep, order expiry, OHLCV snapshot,
  leaderboards, Crier report, scheduled interventions. Per-World, World-local time.
- fast_tick (~5 min): NPC order refresh, moment-detector sweep, nudge eligibility.

Stubs for now — they gain bodies when the engine is wired to persistence.
"""
from arq.connections import RedisSettings

from .config import get_settings


async def daily_market_close(ctx: dict, world_id: str) -> None:
    raise NotImplementedError("Phase 0: wire app.engine to persistence")


async def fast_tick(ctx: dict, world_id: str) -> None:
    raise NotImplementedError("Phase 0: wire NPC schedules to live order books")


class WorkerSettings:
    functions = [daily_market_close, fast_tick]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

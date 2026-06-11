"""Rotate the demo world: retire the current one, seed a fresh mid-course one.

Visitors keep piling into the shared demo world and god-mode guests leave
ceilings and droughts behind — so a public demo should reseed on a schedule
(nightly cron) or whenever it gets weird:

    .venv/bin/python scripts/reset_demo.py

Old demo worlds are unflagged (POST /demo/* always lands in the newest flagged
world) and left in place for inspection; prune them whenever you like.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import World
from scripts.seed_midcourse import DB_URL, main as seed_main


async def unflag_old() -> int:
    engine = create_async_engine(DB_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    n = 0
    async with factory() as db:
        async with db.begin():
            worlds = (await db.scalars(select(World))).all()
            for w in worlds:
                if (w.config or {}).get("is_demo"):
                    w.config = {**w.config, "is_demo": False}
                    n += 1
    await engine.dispose()
    return n


if __name__ == "__main__":
    retired = asyncio.run(unflag_old())
    print(f"retired {retired} old demo world(s)")
    suffix = f"demo{time.strftime('%m%d%H%M')}"
    print(f"seeding fresh demo world (suffix {suffix}) — about a minute…")
    asyncio.run(seed_main(25, suffix, demo=True))
    print("\ndemo reset complete — /?demo=student lands in the new world")

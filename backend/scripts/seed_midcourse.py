"""Seed a mid-course QA world against a live database (default: local Docker PG).

Creates an instructor + 12 bot students with KNOWN passwords, then simulates
N days through the real service layer (same bots as test_semester.py), leaving
a world mid-week-4: price history with the festival spike and drought on the
charts, facilities built, the glowdye auctions ahead.

Usage (from backend/):
    .venv/bin/python scripts/seed_midcourse.py            # 25 days
    .venv/bin/python scripts/seed_midcourse.py --days 25 --suffix 2

Accounts (password for ALL: agora-qa):
    qa{suffix}.instructor@agora-u.edu    instructor / god mode
    qa{suffix}.student00..11@agora-u.edu students (00=trader, see PERSONAS)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Player, World
from app.pedagogy.bank import QUESTIONS
from app.pedagogy.tutor import answer_check, next_check
from app.services import auth as auth_svc
from app.services import worlds as worlds_svc
from app.services.close import run_daily_close
from app.services.common import GameError
from app.services.npc import refresh_npc_orders
from tests.bots import PERSONAS, Bot, bot_day, form_cartel

# How often each persona gets MCQ tutor checks right — variance makes the
# instructor's mastery heatmap worth looking at.
CHECK_SKILL = {"trader": 0.85, "producer": 0.8, "angler": 0.6,
               "tycoon": 0.75, "cartelist": 0.5}


async def bot_tutor_check(db, world, bot: Bot) -> None:
    """Answer today's contextual check if it's an MCQ (free-response would
    invoke the live LLM grader — not for seeding)."""
    player = await db.get(Player, bot.player_id)
    check = await next_check(db, world, player)
    if not check or check["kind"] != "mcq":
        return
    q = QUESTIONS[check["question_id"]]
    if bot.rng.random() < CHECK_SKILL.get(bot.persona, 0.7):
        answer = q.answer
    else:
        answer = (q.answer + 1 + bot.rng.randint(0, max(0, len(q.choices) - 2))) \
            % len(q.choices)
    await answer_check(db, world, player, q.id, str(answer))

DB_URL = os.environ.get(
    "AGORA_DATABASE_URL", "postgresql+asyncpg://agora:agora@localhost:5432/agora"
)
PASSWORD = "agora-qa"


async def main(days: int, suffix: str, demo: bool = False) -> None:
    tag = f"qa{suffix}"
    engine = create_async_engine(DB_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        async with db.begin():
            try:
                prof = await auth_svc.register(
                    db, f"{tag}.instructor@agora-u.edu", "Prof. Marshall", PASSWORD
                )
            except GameError:
                sys.exit(
                    f"{tag}.instructor@agora-u.edu already exists — rerun with "
                    f"a different --suffix (or wipe the DB volume)."
                )
            prof.is_instructor = True
            world = await worlds_svc.create_world(
                db, prof, "Econ 101 (QA mid-course)", f"QA-{tag}",
                {"expected_students": len(PERSONAS), "pacing": "calendar",
                 "rng_seed": f"qa-testbed-{suffix or 1}",
                 **({"is_demo": True} if demo else {})},
            )
            world_id, join_code = world.id, world.join_code
            bots: list[Bot] = []
            for i, persona in enumerate(PERSONAS):
                u = await auth_svc.register(
                    db, f"{tag}.student{i:02d}@agora-u.edu",
                    f"{persona.title()} {i}", PASSWORD,
                )
                player = await worlds_svc.join_world(db, u, join_code)
                bots.append(Bot(player_id=player.id, persona=persona,
                                rng=random.Random(i * 7)))
            tycoons = [b for b in bots if b.persona == "tycoon"]
            tycoons[0].auction = "glowdye-1"
            tycoons[1].auction = "glowdye-2"
            await refresh_npc_orders(db, world)

    cartel_formed = False
    for day in range(1, days + 1):
        async with factory() as db:
            async with db.begin():
                world = await db.get(World, world_id)
                week = world.current_week
                if week >= 7 and not cartel_formed:
                    await form_cartel(db, world, bots)
                    cartel_formed = True
                for bot in bots:
                    await bot_day(db, world, bot, day, week)
                    if bot.rng.random() < 0.7:
                        await bot_tutor_check(db, world, bot)
                await run_daily_close(db, world)
        print(f"  closed day {day} (week {week})")

    async with factory() as db:
        world = await db.get(World, world_id)
        print(f"\nworld ready: week {world.current_week}, day {world.world_day}, "
              f"state {world.state}")
        print(f"  join code:  {join_code}")
        print(f"  instructor: {tag}.instructor@agora-u.edu / {PASSWORD}")
        print(f"  students:   {tag}.student00..{len(PERSONAS)-1:02d}@agora-u.edu / {PASSWORD}")
        print(f"  world_id:   {world_id}")
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None,
                    help="days to simulate (0 = clean-slate day one)")
    ap.add_argument("--week", type=int, default=None,
                    help="seed to mid-week N (overrides --days)")
    ap.add_argument("--suffix", default="", help="suffix for account emails (reruns)")
    ap.add_argument("--demo", action="store_true",
                    help="mark as THE demo world (POST /demo/* lands here)")
    args = ap.parse_args()
    days = args.days
    if args.week is not None:
        days = max(0, args.week * 7 - 3)  # lands mid-week, events fresh on charts
    if days is None:
        days = 25
    asyncio.run(main(days, args.suffix, args.demo))

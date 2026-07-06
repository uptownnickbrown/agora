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
# instructor's mastery heatmap worth looking at. Calibrated to read like a
# real section: a couple of stars, a solid middle, one or two strugglers.
CHECK_SKILL = {"trader": 0.9, "producer": 0.85, "angler": 0.72,
               "tycoon": 0.82, "cartelist": 0.6}

# Seeded classmates read like a roster, not a bot farm — index-aligned with
# PERSONAS (Maya T. is the trader, Jordan P. the producer, and so on).
STUDENT_NAMES = ["Maya T.", "Jordan P.", "Sam K.", "Priya N.", "Diego R.",
                 "Amara O.", "Ethan L.", "Zoe W.", "Marcus J.", "Lena F.",
                 "Omar H.", "Grace C."]


async def bot_tutor_check(db, world, bot: Bot) -> None:
    """Answer today's contextual check if it's an MCQ (free-response would
    invoke the live LLM grader — not for seeding)."""
    player = await db.get(Player, bot.player_id)
    check = await next_check(db, world, player)
    if not check or check["kind"] != "mcq":
        return
    q = QUESTIONS[check["question_id"]]
    answer = _mcq_answer(bot, q, CHECK_SKILL.get(bot.persona, 0.7))
    await answer_check(db, world, player, q.id, str(answer))


def _mcq_answer(bot: Bot, q, p_correct: float) -> int:
    if bot.rng.random() < p_correct:
        return q.answer
    return (q.answer + 1 + bot.rng.randint(0, max(0, len(q.choices) - 2))) \
        % len(q.choices)


async def practice_sweep(db, world, bot: Bot) -> None:
    """Backfill practice the way real students use the Study: each bot
    revisits (nearly) every unlocked objective and answers 2-3 items, so by
    mid-course the heatmap is dense — strengths, developing bands, and a
    few honest reds — instead of a sparse grid of first attempts."""
    from app.pedagogy.bank import LEARNING_OBJECTIVES

    player = await db.get(Player, bot.player_id)
    base = CHECK_SKILL.get(bot.persona, 0.75)
    for lo in LEARNING_OBJECTIVES.values():
        if lo.week > world.current_week:
            continue
        if bot.rng.random() < 0.06:
            continue  # the odd not-yet-assessed cell keeps the legend honest
        pool = [q for q in QUESTIONS.values()
                if lo.id in q.los and q.kind == "mcq"]
        if not pool:
            continue
        # Per-student-per-topic aptitude: even strong students have a topic
        # that wobbles, weak students a topic that clicks.
        p = min(0.97, max(0.3, bot.rng.gauss(base, 0.1)))
        n = 2 + (1 if bot.rng.random() < 0.5 else 0)
        for q in bot.rng.sample(pool, min(len(pool), n)):
            await answer_check(db, world, player, q.id,
                               str(_mcq_answer(bot, q, p)))

# Use the app's normalized URL, not the raw env var: prod sets
# AGORA_DATABASE_URL as `postgresql://…` (no driver), which SQLAlchemy would
# route to psycopg2 (not installed) instead of asyncpg. get_settings() applies
# the same `+asyncpg` normalization the app uses everywhere.
from app.config import get_settings  # noqa: E402

DB_URL = get_settings().database_url
PASSWORD = "agora-qa"


async def main(days: int, suffix: str, demo: bool = False,
               candidate: bool = False):
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
            # Demo worlds pin ONE rng seed so every nightly rotation replays
            # the identical semester — charts, events, and the committed demo
            # playbook/brief artifacts all stay in agreement.
            rng_seed = ("agora-demo" if (demo or candidate)
                        else f"qa-testbed-{suffix or 1}")
            # Demo worlds carry a public-facing name: it shows in the Monday
            # Brief subject line and the instructor header.
            title, section = (("Econ 101", "Demo Section")
                              if (demo or candidate)
                              else ("Econ 101 (QA mid-course)", f"QA-{tag}"))
            world = await worlds_svc.create_world(
                db, prof, title, section,
                {"expected_students": len(PERSONAS), "pacing": "calendar",
                 "rng_seed": rng_seed,
                 **({"is_demo": True} if demo else {}),
                 **({"demo_candidate": True} if candidate else {})},
            )
            world_id, join_code = world.id, world.join_code
            bots: list[Bot] = []
            for i, persona in enumerate(PERSONAS):
                u = await auth_svc.register(
                    db, f"{tag}.student{i:02d}@agora-u.edu",
                    STUDENT_NAMES[i % len(STUDENT_NAMES)], PASSWORD,
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

    # Study-style practice backfill: dense heatmap, realistic distribution.
    if days > 0:
        async with factory() as db:
            async with db.begin():
                world = await db.get(World, world_id)
                for bot in bots:
                    await practice_sweep(db, world, bot)
        print("  practice sweep complete (mastery backfilled)")

    async with factory() as db:
        world = await db.get(World, world_id)
        print(f"\nworld ready: week {world.current_week}, day {world.world_day}, "
              f"state {world.state}")
        print(f"  join code:  {join_code}")
        print(f"  instructor: {tag}.instructor@agora-u.edu / {PASSWORD}")
        print(f"  students:   {tag}.student00..{len(PERSONAS)-1:02d}@agora-u.edu / {PASSWORD}")
        print(f"  world_id:   {world_id}")
    await engine.dispose()
    return world_id


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

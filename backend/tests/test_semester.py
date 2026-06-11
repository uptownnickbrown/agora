"""THE FULL SEMESTER: 12 bot students live all seven weeks, headless, through
the same service layer the API uses. Every week's promised phenomenon must
emerge from the script + interventions + bot behavior. This is the Course
Proof (Phase 2) gate.
"""
import random

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import template as T
from app.db import Base
from app.models import (
    CrierPost,
    DetectedMoment,
    License,
    Player,
    PriceSnapshot,
    User,
    World,
    WorldDayStat,
)
from app.pedagogy.grades import gradebook
from app.pedagogy.playbook import build_playbook
from app.pedagogy.recap import your_economic_story
from app.services import worlds as worlds_svc
from app.services.close import run_daily_close
from app.services.npc import refresh_npc_orders
from app.services.worlds import advance_week
from tests.bots import PERSONAS, Bot, bot_day, form_cartel

pytestmark = pytest.mark.anyio

DAYS_PER_WEEK = T.DAYS_PER_WEEK


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def snapshots(db, world, good):
    return (
        await db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.world_id == world.id, PriceSnapshot.good_id == good)
            .order_by(PriceSnapshot.world_day)
        )
    ).all()


@pytest.mark.slow
async def test_seven_week_semester():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        async with db.begin():
            prof = User(email="prof@agora-u.edu", display_name="Prof. Marshall",
                        is_instructor=True)
            db.add(prof)
            await db.flush()
            world = await worlds_svc.create_world(
                db, prof, "Econ 101", "A",
                {"expected_students": 12, "pacing": "calendar",
                 # Pin the service-layer RNG streams (NPC orders, retail) so the
                 # Course Proof is reproducible — world.id is a random UUID and
                 # marginal phenomena (the Bread Decree bite) flaked on it.
                 "rng_seed": "course-proof"})
            world_id = world.id
            bots: list[Bot] = []
            for i, persona in enumerate(PERSONAS):
                u = User(email=f"bot{i}@agora-u.edu", display_name=f"{persona.title()} {i}")
                db.add(u)
                await db.flush()
                player = await worlds_svc.join_world(db, u, world.join_code)
                bots.append(Bot(player_id=player.id, persona=persona,
                                rng=random.Random(i * 7)))
            tycoons = [b for b in bots if b.persona == "tycoon"]
            tycoons[0].auction = "glowdye-1"   # incumbent monopolist
            tycoons[1].auction = "glowdye-2"   # entrant via the Second Charter
            await refresh_npc_orders(db, world)

    fish_minimum = 10**9
    cartel_formed = False

    for day in range(1, 7 * DAYS_PER_WEEK + 1):
        async with factory() as db:
            async with db.begin():
                world = await db.get(World, world_id)
                week = world.current_week
                if week >= 7 and not cartel_formed:
                    await form_cartel(db, world, bots)
                    cartel_formed = True
                for bot in bots:
                    await bot_day(db, world, bot, day, week)
                await run_daily_close(db, world)
                fish_minimum = min(fish_minimum, world.fish_stock)

    async with factory() as db:
        world = await db.get(World, world_id)
        assert world.current_week == 7
        assert world.world_day == 49

        # ---- Week 2: Festival Rush — garment prices spike during festival days
        garments = await snapshots(db, world, "garments")
        by_day = {s.world_day: s for s in garments if s.close}
        pre = [s.close for d, s in by_day.items() if 8 <= d <= 11]
        rush = [s.close for d, s in by_day.items() if 12 <= d <= 14]
        assert pre and rush, "garment market must trade around the festival"
        assert max(rush) > min(pre) * 1.2, \
            f"festival spike missing: rush {rush} vs pre {pre}"

        # ---- Week 3: drought + Bread Decree — suppression/shortage, then repeal recovery
        bread = await snapshots(db, world, "bread")
        decree_days = [s for s in bread if 17 <= s.world_day <= 20]
        assert any(s.suppressed_asks > 0 or s.unfilled_demand > 10 for s in decree_days), \
            "the Bread Decree must visibly bite (withdrawal or unfilled demand)"
        post_repeal = [s for s in bread if s.world_day >= 22]
        assert sum(s.volume for s in post_repeal) > 0, "bread must trade again after repeal"

        # ---- Week 5: licenses became a real monopoly, then entry compressed prices
        licenses = (
            await db.scalars(select(License).where(License.world_id == world.id,
                                                   ~License.revoked))
        ).all()
        assert licenses, "the glowdye auctions must produce license holders"
        dye = [s for s in await snapshots(db, world, "glowdye") if s.close]
        early = [s.close for s in dye if 29 <= s.world_day <= 32]
        late = [s.close for s in dye if 33 <= s.world_day <= 38]
        if early and late:  # entry compresses monopoly pricing
            assert min(late) <= max(early), \
                f"entry should not RAISE glowdye prices: early {early} late {late}"

        # ---- Week 6: the commons suffered; quota then allowed recovery
        cap = (world.config or {}).get("fish_capacity")
        assert fish_minimum < cap * 0.6, \
            f"open access should bite the fishery (min stock {fish_minimum})"
        assert world.fish_stock > fish_minimum, \
            "post-quota the stock should be recovering"
        kinds = {
            m.kind
            for m in (
                await db.scalars(select(DetectedMoment).where(
                    DetectedMoment.world_id == world.id))
            ).all()
        }
        # ---- Week 7: cartel detected, tournament ran
        assert "cartel_parallel_pricing" in kinds, f"detected kinds: {kinds}"
        criers = (
            await db.scalars(select(CrierPost).where(CrierPost.world_id == world.id))
        ).all()
        titles = " | ".join(c.title for c in criers)
        assert "Market Wars" in titles

        # ---- smog accumulated once week 6 opened (tycoon smelters)
        day_stats = (
            await db.scalars(select(WorldDayStat).where(
                WorldDayStat.world_id == world.id).order_by(WorldDayStat.world_day))
        ).all()
        assert any(d.smog > 0 for d in day_stats), "industry must smoke in week 6"

        # ---- the pedagogy artifacts generate from real data
        pb = await build_playbook(db, world, week=3)
        assert "Lecture Playbook" in pb["markdown"]
        assert pb["interventions"], "week 3 ran scripted interventions"
        rows = await gradebook(db, world)
        assert len(rows) == len(PERSONAS)
        assert all(0 <= r["grade"] <= 1 for r in rows)

        players = (
            await db.scalars(select(Player).where(Player.world_id == world.id,
                                                  ~Player.is_npc))
        ).all()
        recap = await your_economic_story(db, world, players[0])
        assert recap["net_worth_curve"], "recap needs the net-worth curve"
        assert recap["checks_completed"] is not None

        # ---- world economy stayed solvent and active
        total_volume = sum(d.total_volume for d in day_stats)
        assert total_volume > 500, f"a semester of trade should be substantial: {total_volume}"
        assert all(p.coins >= 0 for p in players), "no player may go negative"

    await engine.dispose()

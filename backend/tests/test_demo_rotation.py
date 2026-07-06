"""The blue-green demo rotation: a failed seed must never touch the live
demo world, and the flip must be atomic and guarded."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import make_world, register

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _set_world(session_factory, wid, **attrs):
    from app.models import World

    async with session_factory() as db:
        async with db.begin():
            world = await db.get(World, uuid.UUID(wid))
            for k, v in attrs.items():
                setattr(world, k, v)


async def _get_world(session_factory, wid):
    from app.models import World

    async with session_factory() as db:
        world = await db.get(World, uuid.UUID(wid))
        return {"is_demo": bool((world.config or {}).get("is_demo")),
                "candidate": bool((world.config or {}).get("demo_candidate")),
                "state": world.state}


async def test_demo_rotation_blue_green(client, session_factory, monkeypatch):
    import scripts.seed_midcourse as seed_mod
    from app import worker
    from app.models import World

    monkeypatch.setattr(worker, "_factory", session_factory)

    # A stale live demo world…
    prof = await register(client, name="Prof Old")
    old = await make_world(client, prof["token"])
    async with session_factory() as db:
        async with db.begin():
            world = await db.get(World, uuid.UUID(old["world_id"]))
            world.config = {**(world.config or {}), "is_demo": True}
            world.created_at = datetime.now(timezone.utc) - timedelta(days=2)

    # (a) The seed dies mid-run: the old demo world stays live, untouched.
    async def boom(days, suffix, demo=False, candidate=False):
        raise RuntimeError("connection dropped")

    monkeypatch.setattr(seed_mod, "main", boom)
    assert await worker.demo_reset({}) == 0
    state = await _get_world(session_factory, old["world_id"])
    assert state["is_demo"] and state["state"] != "epilogue"

    # (b) The seed succeeds: candidate world flips live, old world retires.
    prof2 = await register(client, name="Prof New")
    new = await make_world(client, prof2["token"])

    async def fake_seed(days, suffix, demo=False, candidate=False):
        assert candidate and not demo, "rotation must seed unflagged candidates"
        async with session_factory() as db:
            async with db.begin():
                world = await db.get(World, uuid.UUID(new["world_id"]))
                world.config = {**(world.config or {}), "demo_candidate": True}
        return uuid.UUID(new["world_id"])

    monkeypatch.setattr(seed_mod, "main", fake_seed)
    assert await worker.demo_reset({}) == 1
    old_state = await _get_world(session_factory, old["world_id"])
    new_state = await _get_world(session_factory, new["world_id"])
    assert not old_state["is_demo"] and old_state["state"] == "epilogue"
    assert new_state["is_demo"] and not new_state["candidate"]
    assert new_state["state"] != "epilogue"

    # (c) Freshness guard: the just-flipped world blocks another rotation…
    assert await worker.demo_reset({}) == 0
    # …but a manual run (force) goes through.
    assert await worker.demo_reset({}, force=True) == 1


async def test_demo_rotation_retires_stale_candidates(client, session_factory,
                                                      monkeypatch):
    import scripts.seed_midcourse as seed_mod
    from app import worker
    from app.models import World

    monkeypatch.setattr(worker, "_factory", session_factory)

    # A leftover candidate from a failed seed two days ago…
    prof = await register(client, name="Prof Leftover")
    stale = await make_world(client, prof["token"])
    async with session_factory() as db:
        async with db.begin():
            world = await db.get(World, uuid.UUID(stale["world_id"]))
            world.config = {**(world.config or {}), "demo_candidate": True}
            world.created_at = datetime.now(timezone.utc) - timedelta(days=2)

    prof2 = await register(client, name="Prof Fresh")
    new = await make_world(client, prof2["token"])

    async def fake_seed(days, suffix, demo=False, candidate=False):
        return uuid.UUID(new["world_id"])

    monkeypatch.setattr(seed_mod, "main", fake_seed)
    assert await worker.demo_reset({}, force=True) == 1
    stale_state = await _get_world(session_factory, stale["world_id"])
    assert stale_state["state"] == "epilogue"


async def test_ops_rotate_endpoint(client, monkeypatch):
    from app.config import get_settings

    # disabled without a configured token
    r = await client.post("/admin/demo/rotate",
                          headers={"X-Agora-Ops-Token": "anything"})
    assert r.status_code == 403

    monkeypatch.setattr(get_settings(), "ops_token", "sekrit")
    r = await client.post("/admin/demo/rotate",
                          headers={"X-Agora-Ops-Token": "wrong"})
    assert r.status_code == 403

    enqueued = []

    class FakePool:
        async def enqueue_job(self, name, **kw):
            enqueued.append((name, kw))

            class J:
                job_id = "job-1"

            return J()

        async def close(self):
            pass

    async def fake_create_pool(*a, **k):
        return FakePool()

    import arq

    monkeypatch.setattr(arq, "create_pool", fake_create_pool)
    r = await client.post("/admin/demo/rotate",
                          headers={"X-Agora-Ops-Token": "sekrit"})
    assert r.status_code == 200 and r.json()["enqueued"] == "job-1"
    assert enqueued == [("demo_reset", {"force": True})]


def test_seeder_is_importable_after_path_fix():
    """Regression for the prod bug where demo_reset silently failed: scripts/
    and tests/ aren't installed packages, so the seeder import raised
    ImportError (caught, logged, never rotated). _ensure_seeder_importable must
    make the real import resolve."""
    import importlib
    import sys

    from app import worker

    # simulate the installed-copy case where the source root isn't on the path
    for mod in ("scripts", "scripts.seed_midcourse"):
        sys.modules.pop(mod, None)
    worker._ensure_seeder_importable()
    seed = importlib.import_module("scripts.seed_midcourse")
    assert callable(seed.main)


async def test_demo_visitor_lands_furnished_and_hidden(client, session_factory):
    """A demo visitor drops into the MIDDLE of the course: stocked shop,
    facilities, mastery history, a streak — and stays out of the instructor's
    heatmap/gradebook/roster (the curated class, not a visitor trail)."""
    import uuid as _uuid

    from app.models import World
    from tests.conftest import hdr, register, make_world

    prof = await register(client, name="Prof Demo")
    world = await make_world(client, prof["token"])
    async with session_factory() as db:
        async with db.begin():
            w = await db.get(World, _uuid.UUID(world["world_id"]))
            w.config = {**(w.config or {}), "is_demo": True}
            w.current_week, w.world_day = 4, 25

    r = await client.post("/demo/student")
    assert r.status_code == 200, r.text
    visitor = r.json()
    vh = hdr(visitor["token"])
    wid = visitor["world_id"]

    state = (await client.get(f"/worlds/{wid}/state", headers=vh)).json()
    assert state["player"]["coins"] > 200, "mid-course purse, not day-one"
    assert state["facilities"], "facilities already humming"
    assert state["achievements"], "a little swagger"
    shop = (await client.get(f"/worlds/{wid}/shop", headers=vh)).json()
    assert shop and any(l["sold_total"] > 0 for l in shop)
    mastery = (await client.get(f"/worlds/{wid}/tutor/mastery", headers=vh)).json()
    assessed = [m for m in mastery if m["pct"] is not None]
    assert len(assessed) >= 6, "a realistic mastery history"
    assert any(m["pct"] <= 40 for m in assessed), "one honest wobble to practice"

    # ...and none of it leaks into the instructor's views.
    ph = hdr(prof["token"])
    heat = (await client.get(f"/worlds/{wid}/instructor/heatmap",
                             headers=ph)).json()
    names = [s["merchant"] for s in heat["students"]]
    assert visitor["merchant"] not in names
    grades = (await client.get(f"/worlds/{wid}/instructor/gradebook",
                               headers=ph)).json()
    assert all(g["merchant"] != visitor["merchant"] for g in grades)
    dash = (await client.get(f"/worlds/{wid}/instructor/dashboard",
                             headers=ph)).json()
    assert all(p["merchant"] != visitor["merchant"] for p in dash["roster"])

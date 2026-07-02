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

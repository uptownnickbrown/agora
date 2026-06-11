"""The Monday Brief: due-stamping on week advance, idempotent sweep, opt-out,
content, manual endpoints, and magic-link email logging."""
import uuid

import pytest
from sqlalchemy import select

from app.models import EmailLog, Player, World
from app.services.digest import build_digest, process_due_digests

from tests.conftest import hdr, join, make_world, register


@pytest.fixture()
def anyio_backend():
    return "asyncio"


async def _world(db_factory, world_id: str) -> World:
    async with db_factory() as db:
        return await db.get(World, uuid.UUID(world_id))


async def _email_logs(db_factory, kind: str) -> list[EmailLog]:
    async with db_factory() as db:
        return list(await db.scalars(select(EmailLog).where(EmailLog.kind == kind)))


@pytest.mark.anyio
async def test_advance_week_stamps_digest_due(client, session_factory):
    inst = await register(client)
    out = await make_world(client, inst["token"])
    r = await client.post(f"/worlds/{out['world_id']}/instructor/advance-week",
                          headers=hdr(inst["token"]))
    assert r.status_code == 200
    world = await _world(session_factory, out["world_id"])
    # advancing 1 -> 2 means week 1 just ended and is due
    assert (world.config or {}).get("digest_due_week") == world.current_week - 1


@pytest.mark.anyio
async def test_sweep_sends_once_and_is_idempotent(client, session_factory):
    inst_email = f"prof-{uuid.uuid4().hex[:8]}@test.edu"
    inst = await register(client, email=inst_email)
    out = await make_world(client, inst["token"])
    stu = await register(client)
    await join(client, stu["token"], out["join_code"])
    await client.post(f"/worlds/{out['world_id']}/instructor/advance-week",
                      headers=hdr(inst["token"]))

    sent = await process_due_digests(session_factory)
    assert sent == 1
    logs = await _email_logs(session_factory, "digest")
    assert len(logs) == 1
    assert logs[0].status == "console"
    assert logs[0].to_email == inst_email
    assert "Lecture Playbook" in logs[0].body_text

    # Second sweep: nothing due anymore.
    assert await process_due_digests(session_factory) == 0
    assert len(await _email_logs(session_factory, "digest")) == 1
    world = await _world(session_factory, out["world_id"])
    assert world.config.get("digest_sent_week") == world.config.get("digest_due_week")


@pytest.mark.anyio
async def test_opt_out_stamps_without_sending(client, session_factory):
    inst = await register(client)
    out = await make_world(client, inst["token"])
    r = await client.post(f"/worlds/{out['world_id']}/instructor/digest/settings",
                          headers=hdr(inst["token"]), json={"enabled": False})
    assert r.status_code == 200
    await client.post(f"/worlds/{out['world_id']}/instructor/advance-week",
                      headers=hdr(inst["token"]))
    assert await process_due_digests(session_factory) == 0
    assert await _email_logs(session_factory, "digest") == []
    world = await _world(session_factory, out["world_id"])
    assert world.config.get("digest_sent_week") == world.config.get("digest_due_week")


@pytest.mark.anyio
async def test_digest_flags_inactive_students(client, session_factory):
    inst = await register(client)
    out = await make_world(client, inst["token"])
    stu = await register(client)
    joined = await join(client, stu["token"], out["join_code"])
    async with session_factory() as db:
        async with db.begin():
            world = await db.get(World, uuid.UUID(out["world_id"]))
            world.world_day = 8
            player = await db.scalar(
                select(Player).where(Player.world_id == world.id, ~Player.is_npc))
            player.last_active_day = 1
    async with session_factory() as db:
        world = await db.get(World, uuid.UUID(out["world_id"]))
        msg = await build_digest(db, world, 1)
    assert joined["merchant"] in msg.text
    assert "need a nudge" in msg.text
    assert msg.attachments and msg.attachments[0][0].endswith(".csv")
    assert "email,merchant" in msg.attachments[0][2]


@pytest.mark.anyio
async def test_digest_endpoints(client, session_factory):
    inst = await register(client)
    out = await make_world(client, inst["token"])
    r = await client.get(f"/worlds/{out['world_id']}/instructor/digest/settings",
                         headers=hdr(inst["token"]))
    assert r.status_code == 200 and r.json()["enabled"] is True

    r = await client.get(f"/worlds/{out['world_id']}/instructor/digest/preview",
                         headers=hdr(inst["token"]))
    assert r.status_code == 200
    assert "Lecture Playbook" in r.json()["markdown"]

    r = await client.post(f"/worlds/{out['world_id']}/instructor/digest/send",
                          headers=hdr(inst["token"]))
    assert r.status_code == 200
    assert r.json()["sent_to"]
    assert len(await _email_logs(session_factory, "digest")) == 1


@pytest.mark.anyio
async def test_scores_endpoint_shape(client, session_factory):
    inst = await register(client)
    out = await make_world(client, inst["token"])
    stu = await register(client)
    await join(client, stu["token"], out["join_code"])
    r = await client.get(f"/worlds/{out['world_id']}/instructor/scores",
                         headers=hdr(inst["token"]))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert set(rows[0]) == {"email", "score", "max_score", "world_week"}
    assert rows[0]["max_score"] == 100


@pytest.mark.anyio
async def test_magic_link_logged_when_not_console(client, session_factory, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "resend_api_key", "")  # forces EmailError path
    email = f"magic-{uuid.uuid4().hex[:8]}@test.edu"
    await register(client, email=email)
    r = await client.post("/auth/magic/request", json={"email": email})
    assert r.status_code == 200
    assert "dev_token" not in r.json()  # no token leak outside console mode
    logs = await _email_logs(session_factory, "magic_link")
    assert len(logs) == 1 and logs[0].status == "failed"

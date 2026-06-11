import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.deps import set_session_factory
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def session_factory(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    set_session_factory(factory)
    return factory


@pytest.fixture()
async def client(session_factory):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register(client, email=None, name="Test User") -> dict:
    email = email or f"{uuid.uuid4().hex[:10]}@test.edu"
    r = await client.post("/auth/register", json={"email": email, "display_name": name})
    assert r.status_code == 200, r.text
    return r.json()


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def make_world(client, instructor_token: str, **kwargs) -> dict:
    r = await client.post("/instructor/worlds", headers=hdr(instructor_token),
                          json={"course_title": "Econ 101", "section_name": "A",
                                **kwargs})
    assert r.status_code == 200, r.text
    return r.json()


async def join(client, token: str, join_code: str) -> dict:
    r = await client.post("/join", headers=hdr(token), json={"join_code": join_code})
    assert r.status_code == 200, r.text
    return r.json()


async def quiet_npcs(session_factory, world_id: str) -> None:
    """Pause NPC schedules and clear their resting orders so tests can make
    exact assertions about student-to-student trades."""
    import uuid as _uuid

    from sqlalchemy import select, update

    from app.models import DbOrder, NPCSchedule, Player

    async with session_factory() as db:
        async with db.begin():
            wid = _uuid.UUID(world_id)
            await db.execute(update(NPCSchedule).where(
                NPCSchedule.world_id == wid).values(paused=True))
            npc_ids = (
                await db.scalars(select(Player.id).where(Player.world_id == wid,
                                                         Player.is_npc))
            ).all()
            await db.execute(update(DbOrder).where(
                DbOrder.world_id == wid, DbOrder.player_id.in_(npc_ids),
                DbOrder.status == "open").values(status="cancelled"))


@pytest.fixture()
async def game(client, session_factory):
    """A ready QUIET world (NPCs paused): instructor + 3 students, week 2."""
    instructor = await register(client, name="Prof. Marshall")
    world = await make_world(client, instructor["token"])
    students = []
    for i in range(3):
        s = await register(client, name=f"Student {i}")
        j = await join(client, s["token"], world["join_code"])
        students.append({**s, **j})
    r = await client.post(f"/worlds/{world['world_id']}/instructor/advance-week",
                          headers=hdr(instructor["token"]))
    assert r.status_code == 200
    await quiet_npcs(session_factory, world["world_id"])
    return {"client": client, "instructor": instructor, "world": world,
            "students": students, "world_id": world["world_id"],
            "session_factory": session_factory}

"""WebSocket live feed + platform admin endpoints (sync TestClient: REST and WS
share one event loop, file-backed SQLite with NullPool avoids loop affinity)."""
import asyncio

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from app.db import Base
from app.deps import set_session_factory
from app.main import app
from app.models import User


def _setup(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/ws.db"

    async def create_all():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_all())
    engine = create_async_engine(url, poolclass=NullPool)
    set_session_factory(async_sessionmaker(engine, expire_on_commit=False))
    return url


def test_websocket_trade_feed(tmp_path):
    _setup(tmp_path)
    client = TestClient(app)

    prof = client.post("/auth/register", json={
        "email": "prof@ws.edu", "display_name": "Prof"}).json()
    ph = {"Authorization": f"Bearer {prof['token']}"}
    world = client.post("/instructor/worlds", headers=ph, json={
        "course_title": "E", "section_name": "A"}).json()
    wid = world["world_id"]
    student = client.post("/auth/register", json={
        "email": "s@ws.edu", "display_name": "S"}).json()
    sh = {"Authorization": f"Bearer {student['token']}"}
    client.post("/join", headers=sh, json={"join_code": world["join_code"]})

    with client.websocket_connect(f"/worlds/{wid}/ws?token={student['token']}") as ws:
        book = client.get(f"/worlds/{wid}/markets/grain/book", headers=sh).json()
        assert book["asks"], "NPC asks must be live"
        best_ask = book["asks"][0][0]
        result = client.post(f"/worlds/{wid}/orders", headers=sh, json={
            "good_id": "grain", "side": "buy", "qty": 2, "price": best_ask + 3}).json()
        assert result["trades"], result
        message = ws.receive_json()
        assert message["type"] == "trade"
        assert message["good_id"] == "grain" and message["qty"] >= 1

    # bad token is refused before accept
    try:
        with client.websocket_connect(f"/worlds/{wid}/ws?token=bogus") as ws:
            ws.receive_json()
        refused = False
    except Exception:
        refused = True
    assert refused


def test_admin_endpoints(tmp_path):
    url = _setup(tmp_path)
    client = TestClient(app)

    prof = client.post("/auth/register", json={
        "email": "prof2@ws.edu", "display_name": "Prof"}).json()
    ph = {"Authorization": f"Bearer {prof['token']}"}
    client.post("/instructor/worlds", headers=ph, json={
        "course_title": "Econ 101", "section_name": "B"})

    # not an admin yet
    assert client.get("/admin/overview", headers=ph).status_code == 403

    async def promote():
        engine = create_async_engine(url, poolclass=NullPool)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            async with db.begin():
                await db.execute(update(User).where(
                    User.email == "prof2@ws.edu").values(is_platform_admin=True))
        await engine.dispose()

    asyncio.run(promote())

    overview = client.get("/admin/overview", headers=ph).json()
    assert overview["total_users"] >= 1
    assert any(w["course"] == "Econ 101" for w in overview["worlds"])
    balance = client.get("/admin/balance", headers=ph).json()
    assert balance["balance"]["starting_coins"] == 200
    assert "grain" in balance["goods"]

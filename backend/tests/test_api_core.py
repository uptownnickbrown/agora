"""API tests: auth, world lifecycle, trading, production, shops, daily close."""
import pytest

from tests.conftest import hdr, join, make_world, register

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_register_login_magic(client):
    r = await client.post("/auth/register", json={
        "email": "pip@agora-u.edu", "display_name": "Pip", "password": "coo-coo-secret"})
    assert r.status_code == 200
    r = await client.post("/auth/login", json={"email": "pip@agora-u.edu",
                                               "password": "coo-coo-secret"})
    assert r.status_code == 200
    token = r.json()["token"]
    r = await client.get("/auth/me", headers=hdr(token))
    assert r.json()["display_name"] == "Pip"

    r = await client.post("/auth/magic/request", json={"email": "pip@agora-u.edu"})
    magic = r.json()["dev_token"]
    r = await client.post("/auth/magic/redeem", json={"token": magic})
    assert r.status_code == 200 and r.json()["token"]

    r = await client.post("/auth/login", json={"email": "pip@agora-u.edu",
                                               "password": "wrong"})
    assert r.status_code == 400


async def test_join_world_unbalanced_endowments(client):
    instructor = await register(client, name="Prof")
    world = await make_world(client, instructor["token"])
    s1 = await register(client)
    s2 = await register(client)
    j1 = await join(client, s1["token"], world["join_code"])
    j2 = await join(client, s2["token"], world["join_code"])
    assert j1["aptitude"] != j2["aptitude"]  # round-robin aptitudes
    r = await client.get(f"/worlds/{world['world_id']}/state", headers=hdr(s1["token"]))
    state = r.json()
    assert state["player"]["coins"] == 200
    assert state["inventory"][j1["aptitude"]] == 30

    r = await client.post("/join", headers=hdr(s1["token"]),
                          json={"join_code": "nonsense"})
    assert r.status_code == 400


async def test_trading_between_students(game):
    client = game["client"]
    wid = game["world_id"]
    alice, bob = game["students"][0], game["students"][1]

    # Alice asks 10 of her aptitude good at 40; Bob lifts it.
    good = alice["aptitude"]
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": good, "side": "sell", "qty": 10, "price": 40})
    assert r.status_code == 200, r.text
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(bob["token"]),
                          json={"good_id": good, "side": "buy", "qty": 4, "price": 45})
    result = r.json()
    assert sum(t["qty"] for t in result["trades"]) == 4
    assert result["trades"][0]["price"] == 40  # resting price execution

    a_state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    b_state = (await client.get(f"/worlds/{wid}/state", headers=hdr(bob["token"]))).json()
    assert a_state["player"]["coins"] == 200 + 160          # sold 4 @ 40
    assert b_state["player"]["coins"] == 200 - 160          # escrowed 180, refunded 20
    assert b_state["inventory"].get(good, 0) == 4


async def test_escrow_refund_on_cancel(game):
    client = game["client"]
    wid = game["world_id"]
    alice = game["students"][0]
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "grain", "side": "buy", "qty": 4, "price": 50})
    order_id = r.json()["order_id"]
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 0  # 200 escrowed... 4*50
    r = await client.delete(f"/worlds/{wid}/orders/{order_id}", headers=hdr(alice["token"]))
    assert r.status_code == 200
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 200


async def test_cannot_sell_what_you_lack(game):
    client = game["client"]
    wid = game["world_id"]
    alice = game["students"][0]
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "bread", "side": "sell", "qty": 5, "price": 100})
    assert r.status_code == 400
    assert "not enough" in r.json()["detail"]


async def test_gather_craft_chain(game):
    client = game["client"]
    wid = game["world_id"]
    alice = game["students"][0]
    good = alice["aptitude"]
    r = await client.post(f"/worlds/{wid}/gather", headers=hdr(alice["token"]),
                          json={"good_id": good, "effort": 4})
    assert r.json()["gathered"] == 12  # aptitude 3x

    if good == "grain":
        r = await client.post(f"/worlds/{wid}/craft", headers=hdr(alice["token"]),
                              json={"output": "flour", "runs": 3})
        assert r.json()["crafted"] == 3
        state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
        assert state["inventory"]["flour"] == 3


async def test_facility_production_at_close(game):
    client = game["client"]
    wid = game["world_id"]
    alice, prof = game["students"][0], game["instructor"]
    r = await client.post(f"/worlds/{wid}/facilities", headers=hdr(alice["token"]),
                          json={"kind": "farm"})
    assert r.status_code == 200, r.text
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    coins_before = state["player"]["coins"]
    grain_before = state["inventory"].get("grain", 0)

    r = await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    assert r.status_code == 200, r.text

    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["inventory"].get("grain", 0) == grain_before + 4  # tier 1 output
    assert state["player"]["coins"] == coins_before - 4  # upkeep


async def test_shop_retail_demand(game):
    client = game["client"]
    wid = game["world_id"]
    alice, prof = game["students"][0], game["instructor"]
    good = alice["aptitude"]
    r = await client.post(f"/worlds/{wid}/shop", headers=hdr(alice["token"]),
                          json={"good_id": good, "price": 25, "qty": 20})
    assert r.status_code == 200, r.text
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    r = await client.get(f"/worlds/{wid}/shop", headers=hdr(alice["token"]))
    listing = r.json()[0]
    assert listing["sold_total"] > 0  # passersby bought something


async def test_npc_liquidity_lets_singleton_trade(client):
    """A lone student can always trade — NPC bots carry thin markets."""
    prof = await register(client, name="Prof Solo")
    world = await make_world(client, prof["token"])
    alice = await register(client)
    await join(client, alice["token"], world["join_code"])
    wid = world["world_id"]
    r = await client.get(f"/worlds/{wid}/markets/grain/book", headers=hdr(alice["token"]))
    book = r.json()
    assert book["asks"], "NPC supply should be resting on the grain book"
    # market-buy against NPC asks
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "grain", "side": "buy", "qty": 3,
                                "price": book["asks"][0][0] + 5})
    assert sum(t["qty"] for t in r.json()["trades"]) == 3


async def test_daily_close_writes_crier_and_snapshots(game):
    client = game["client"]
    wid = game["world_id"]
    prof, alice, bob = game["instructor"], game["students"][0], game["students"][1]
    good = alice["aptitude"]
    await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                      json={"good_id": good, "side": "sell", "qty": 5, "price": 30})
    await client.post(f"/worlds/{wid}/orders", headers=hdr(bob["token"]),
                      json={"good_id": good, "side": "buy", "qty": 5, "price": 35})
    r = await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    assert r.status_code == 200
    r = await client.get(f"/worlds/{wid}/markets/{good}/history", headers=hdr(alice["token"]))
    history = r.json()
    assert history and history[-1]["close"] == 30 and history[-1]["volume"] >= 5
    r = await client.get(f"/worlds/{wid}/crier", headers=hdr(alice["token"]))
    posts = r.json()
    assert any(p["kind"] == "market_report" for p in posts)


async def test_effort_is_scarce(game):
    client = game["client"]
    wid = game["world_id"]
    alice = game["students"][0]
    r = await client.post(f"/worlds/{wid}/gather", headers=hdr(alice["token"]),
                          json={"good_id": alice["aptitude"], "effort": 20})
    assert r.status_code == 200
    r = await client.post(f"/worlds/{wid}/gather", headers=hdr(alice["token"]),
                          json={"good_id": alice["aptitude"], "effort": 5})
    assert r.status_code == 400  # the scarcity primitive bites


async def test_students_cannot_touch_instructor_routes(game):
    client = game["client"]
    wid = game["world_id"]
    alice = game["students"][0]
    for path in (f"/worlds/{wid}/instructor/dashboard",
                 f"/worlds/{wid}/instructor/gradebook"):
        r = await client.get(path, headers=hdr(alice["token"]))
        assert r.status_code == 403
    r = await client.post(f"/worlds/{wid}/instructor/interventions",
                          headers=hdr(alice["token"]),
                          json={"kind": "stimulus", "params": {"amount": 9999}})
    assert r.status_code == 403


async def test_world_isolation(client):
    """Hard tenancy: a player in world A cannot act in world B."""
    prof = await register(client, name="Prof")
    world_a = await make_world(client, prof["token"])
    world_b = await make_world(client, prof["token"])
    s = await register(client)
    await join(client, s["token"], world_a["join_code"])
    r = await client.get(f"/worlds/{world_b['world_id']}/state", headers=hdr(s["token"]))
    assert r.status_code == 403

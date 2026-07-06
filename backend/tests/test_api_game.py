"""Game-system tests: interventions, fun layer, licenses, compacts, pedagogy,
gradebook, playbook, recap, anti-ruin."""
import pytest

from tests.conftest import hdr, join, make_world, register

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def advance_to_week(client, game, week: int):
    prof = game["instructor"]
    wid = game["world_id"]
    for _ in range(week - 2):  # game fixture starts at week 2
        r = await client.post(f"/worlds/{wid}/instructor/advance-week",
                              headers=hdr(prof["token"]))
        assert r.status_code == 200
    return wid


async def test_price_ceiling_suppresses_asks(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    good = alice["aptitude"]
    r = await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                          json={"kind": "price_ceiling", "params": {"good": good, "price": 20}})
    assert r.status_code == 200
    assert "decree" in r.json()["crier"].lower() or "royal" in r.json()["crier"].lower()
    # Alice tries to sell above the ceiling: suppressed (seller withdrawal)
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": good, "side": "sell", "qty": 5, "price": 60})
    assert r.json()["status"] == "suppressed"
    # Buyer above ceiling clamps to legal max
    bob = game["students"][1]
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(bob["token"]),
                          json={"good_id": good, "side": "buy", "qty": 2, "price": 90})
    assert r.json()["status"] == "open"  # rests at the clamped ceiling price
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(bob["token"]))).json()
    assert state["player"]["coins"] == 200 - 2 * 20  # escrowed at ceiling, not 90


async def test_tax_collected_on_fills(game):
    client, wid = game["client"], game["world_id"]
    prof, alice, bob = game["instructor"], game["students"][0], game["students"][1]
    good = alice["aptitude"]
    await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                      json={"kind": "tax", "params": {"good": good, "per_unit": 5}})
    await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                      json={"good_id": good, "side": "sell", "qty": 4, "price": 30})
    await client.post(f"/worlds/{wid}/orders", headers=hdr(bob["token"]),
                      json={"good_id": good, "side": "buy", "qty": 4, "price": 30})
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 200 + 4 * (30 - 5)  # proceeds minus tax


async def test_stimulus_and_scheduled_intervention(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    r = await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                          json={"kind": "stimulus", "params": {"amount": 50},
                                "schedule_day": 2})
    assert r.json()["scheduled"]
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))  # day 0->1
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))  # day 1->2
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))  # fires day 2
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] >= 250


async def _todays_puzzle(game):
    """Peek at today's answer key through the service layer (tests only)."""
    import uuid as _uuid

    from app.models import World
    from app.services.fun import puzzle_of_the_day

    async with game["session_factory"]() as db:
        world = await db.get(World, _uuid.UUID(game["world_id"]))
        return puzzle_of_the_day(world)


async def test_puzzle_flawless_solve(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.get(f"/worlds/{wid}/puzzle", headers=hdr(alice["token"]))
    p = r.json()
    assert len(p["terms"]) == 16
    assert p["mistakes_left"] == 4 and not p["finished"] and p["found"] == []
    key = await _todays_puzzle(game)
    assert sorted(t.lower() for t in p["terms"]) == sorted(
        t.lower() for g in key["groups"] for t in g["terms"])
    out = None
    for g in key["groups"]:
        r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(alice["token"]),
                              json={"terms": g["terms"]})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["result"] == "correct" and out["group"]["name"] == g["name"]
    assert out["solved"] and out["finished"]
    assert out["effort_gained"] == 3  # flawless: +2 plus the +1 bonus
    r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(alice["token"]),
                          json={"terms": key["groups"][0]["terms"]})
    assert r.status_code == 400  # closed for the day
    p = (await client.get(f"/worlds/{wid}/puzzle", headers=hdr(alice["token"]))).json()
    assert p["solved"] and p["streak"] == 1 and len(p["found"]) == 4


async def test_puzzle_mistakes_and_reveal(game):
    client, wid = game["client"], game["world_id"]
    bob = game["students"][1]
    key = await _todays_puzzle(game)
    groups = key["groups"]
    # three from one group plus an outsider: "one away", one mistake burned
    near_miss = groups[0]["terms"][:3] + [groups[1]["terms"][0]]
    r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(bob["token"]),
                          json={"terms": near_miss})
    out = r.json()
    assert out["result"] == "one_away" and out["mistakes_left"] == 3
    # the same wrong set again costs nothing
    r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(bob["token"]),
                          json={"terms": near_miss})
    assert r.json()["result"] == "already_guessed"
    assert r.json()["mistakes_left"] == 3
    # three more distinct wrong guesses end the day
    for i in (1, 2, 3):
        scrambled = [groups[j]["terms"][i] for j in range(4)]
        r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(bob["token"]),
                              json={"terms": scrambled})
        out = r.json()
    assert out["finished"] and not out["solved"] and out["mistakes_left"] == 0
    assert len(out["reveal"]) == 4
    p = (await client.get(f"/worlds/{wid}/puzzle", headers=hdr(bob["token"]))).json()
    assert p["finished"] and not p["solved"] and p["reveal"] is not None


async def test_puzzle_bank_integrity():
    from app.puzzles import PUZZLES

    assert len(PUZZLES) >= 40
    for puzzle in PUZZLES:
        assert len(puzzle) == 4
        terms = [t.lower() for _, ts in puzzle for t in ts]
        assert len(terms) == 16 and len(set(terms)) == 16


async def test_fishing_and_quota(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    caught = 0
    for _ in range(5):
        r = await client.post(f"/worlds/{wid}/fishing/cast", headers=hdr(alice["token"]))
        assert r.status_code == 200
        out = r.json()
        caught += out["qty"]
        assert 900 <= out["bite_ms"] <= 2600 and 0 <= out["nibbles"] <= 2
        if out["qty"]:
            assert len(out["fish"]) == out["qty"]
            assert sum(f["weight"] for f in out["fish"]) == out["weight"]
            assert all(f["species"] and f["size_class"] in ("minnow", "keeper", "prize")
                       for f in out["fish"])
        else:
            assert out["miss_flavor"]
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["effort"] == 20 - 15  # 5 casts * 3 effort
    assert state["inventory"].get("fish", 0) == caught
    # quota of zero blocks all fishing
    await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                      json={"kind": "fishing_quota", "params": {"per_player_per_day": 0}})
    r = await client.post(f"/worlds/{wid}/fishing/cast", headers=hdr(alice["token"]))
    assert r.status_code == 400 and "quota" in r.json()["detail"]


async def test_traveling_merchant(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.get(f"/worlds/{wid}/merchant", headers=hdr(alice["token"]))
    inst = r.json()
    # greedy plan: at each leg buy the good with the best next-port margin
    legs = []
    for i in range(len(inst["ports"]) - 1):
        port, nxt = inst["ports"][i], inst["ports"][i + 1]
        best = max(inst["goods"],
                   key=lambda g: inst["prices"][nxt][g] - inst["prices"][port][g])
        margin = inst["prices"][nxt][best] - inst["prices"][port][best]
        qty = inst["capacity"] if margin > 0 else 0
        # affordability cap is enforced server-side; keep it simple and legal
        legs.append({"port": port, "buy": {best: min(qty, 100 // max(1, inst["prices"][port][best]))}})
    r = await client.post(f"/worlds/{wid}/merchant/submit", headers=hdr(alice["token"]),
                          json={"legs": legs})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["reward"] >= 20
    assert out["best_profit"] >= out["profit"]
    assert 0 <= out["pct_of_best"] <= 100
    r = await client.post(f"/worlds/{wid}/merchant/submit", headers=hdr(alice["token"]),
                          json={"legs": legs})
    assert r.status_code == 400  # one run only
    r = await client.get(f"/worlds/{wid}/merchant", headers=hdr(alice["token"]))
    assert r.json()["completed"] and r.json()["pct_of_best"] == out["pct_of_best"]


async def _todays_haggle(game, player_id: str):
    import uuid as _uuid

    from sqlalchemy import select

    from app.models import HaggleSession

    async with game["session_factory"]() as db:
        return await db.scalar(select(HaggleSession).where(
            HaggleSession.player_id == _uuid.UUID(player_id)))


async def test_haggle_accept_and_close(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.get(f"/worlds/{wid}/haggle", headers=hdr(alice["token"]))
    assert r.status_code == 200, r.text
    deal = r.json()
    assert deal["state"] == "open" and deal["offers_left"] == 3
    assert deal["reservation"] is None  # hidden while the deal is open
    assert deal["side"] == "npc_buys"  # alice holds her aptitude endowment
    session = await _todays_haggle(game, alice["player_id"])
    state0 = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    # a greedy quote gets rejected, burning one offer
    r = await client.post(f"/worlds/{wid}/haggle/offer", headers=hdr(alice["token"]),
                          json={"price": session.reservation * 3})
    out = r.json()
    assert out["result"] == "rejected" and out["offers_left"] == 2 and out["flavor"]
    # quoting their exact ceiling closes the deal at that price
    r = await client.post(f"/worlds/{wid}/haggle/offer", headers=hdr(alice["token"]),
                          json={"price": session.reservation})
    out = r.json()
    assert out["result"] == "accepted" and out["reservation"] == session.reservation
    assert out["left_on_table"] == 0
    state1 = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state1["player"]["coins"] - state0["player"]["coins"] == \
        session.reservation * session.qty
    assert state0["inventory"][session.good_id] - \
        state1["inventory"].get(session.good_id, 0) == session.qty
    assert any(a["id"] == "silver_tongue" for a in state1["achievements"])
    r = await client.post(f"/worlds/{wid}/haggle/offer", headers=hdr(alice["token"]),
                          json={"price": 10})
    assert r.status_code == 400  # one visitor a day
    deal = (await client.get(f"/worlds/{wid}/haggle", headers=hdr(alice["token"]))).json()
    assert deal["state"] == "accepted" and deal["reservation"] == session.reservation


async def test_haggle_walk_away(game):
    client, wid = game["client"], game["world_id"]
    bob = game["students"][1]
    r = await client.get(f"/worlds/{wid}/haggle", headers=hdr(bob["token"]))
    assert r.status_code == 200
    r = await client.post(f"/worlds/{wid}/haggle/walk", headers=hdr(bob["token"]))
    out = r.json()
    assert out["result"] == "declined" and out["reservation"] > 0
    deal = (await client.get(f"/worlds/{wid}/haggle", headers=hdr(bob["token"]))).json()
    assert deal["state"] == "declined"


async def test_daily_bonus_streak(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    # first visit of the join day: streak begins, no coins yet
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["daily_bonus"] is None
    coins0 = state["player"]["coins"]
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    # first visit of the next day: the streak chest opens
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    bonus = state["daily_bonus"]
    assert bonus and bonus["streak"] == 2 and bonus["coins"] == 11
    assert state["player"]["coins"] == coins0 + 11
    # only once per day
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["daily_bonus"] is None


async def test_tutor_checks_update_mastery_and_gradebook(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    answered = 0
    for _ in range(6):
        r = await client.get(f"/worlds/{wid}/tutor/check", headers=hdr(alice["token"]))
        check = r.json()
        if check.get("done"):
            break
        if check["kind"] == "mcq":
            # answer index 1 (most banks correct answers vary; we just need attempts)
            r = await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(alice["token"]),
                                  json={"question_id": check["question_id"], "answer": "1"})
        else:
            r = await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(alice["token"]),
                                  json={"question_id": check["question_id"],
                                        "answer": "prices differ across places so buying low and selling high profits"})
        assert r.status_code == 200
        assert "feedback" in r.json()
        answered += 1
    assert answered >= 3
    r = await client.get(f"/worlds/{wid}/tutor/mastery", headers=hdr(alice["token"]))
    mastery = r.json()
    assert any(m["attempts"] > 0 for m in mastery)

    r = await client.get(f"/worlds/{wid}/instructor/gradebook", headers=hdr(prof["token"]))
    rows = r.json()
    alice_row = next(row for row in rows if row["merchant"] == "Student 0")
    assert alice_row["los_assessed"] > 0
    r = await client.get(f"/worlds/{wid}/instructor/gradebook.csv", headers=hdr(prof["token"]))
    assert "merchant" in r.text and "Student 0" in r.text
    r = await client.get(f"/worlds/{wid}/instructor/heatmap", headers=hdr(prof["token"]))
    assert r.json()["los"]


async def test_tutor_chat_canned_fallback(game):
    """No API key configured in tests — Pip degrades gracefully, stays in character."""
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.post(f"/worlds/{wid}/tutor/chat", headers=hdr(alice["token"]),
                          json={"message": "what is elasticity?"})
    assert r.status_code == 200
    assert len(r.json()["reply"]) > 20
    r = await client.get(f"/worlds/{wid}/tutor/history", headers=hdr(alice["token"]))
    assert len(r.json()) == 2  # user + tutor


async def test_license_auction_to_monopoly(game):
    client = game["client"]
    wid = await advance_to_week(client, game, 5)
    prof, alice, bob = game["instructor"], game["students"][0], game["students"][1]
    # glowdye requires a license even with materials in hand
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "glowdye", "side": "sell", "qty": 1, "price": 300})
    assert r.status_code == 400 and "license" in r.json()["detail"]

    await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                      json={"kind": "license_auction",
                            "params": {"good": "glowdye", "auction_id": "g1",
                                       "licenses": 1, "close_day_offset": 1}})
    r = await client.post(f"/worlds/{wid}/license-bids", headers=hdr(alice["token"]),
                          json={"auction_id": "g1", "amount": 150})
    assert r.status_code == 200
    await client.post(f"/worlds/{wid}/license-bids", headers=hdr(bob["token"]),
                      json={"auction_id": "g1", "amount": 90})
    # two closes -> day advances past the sealed-bid window and resolves it
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 200 - 150
    # the monopolist can now sell; the loser still cannot
    r = await client.post(f"/worlds/{wid}/gather", headers=hdr(alice["token"]),
                          json={"good_id": "herbs", "effort": 4})
    r = await client.post(f"/worlds/{wid}/gather", headers=hdr(alice["token"]),
                          json={"good_id": "ore", "effort": 4})
    r = await client.post(f"/worlds/{wid}/craft", headers=hdr(alice["token"]),
                          json={"output": "glowdye", "runs": 1})
    assert r.status_code == 200, r.text
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "glowdye", "side": "sell", "qty": 1, "price": 500})
    assert r.status_code == 200
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(bob["token"]),
                          json={"good_id": "glowdye", "side": "sell", "qty": 1, "price": 500})
    assert r.status_code == 400


async def test_compacts_and_cartel_detection(game):
    client = game["client"]
    wid = await advance_to_week(client, game, 7)
    prof = game["instructor"]
    alice, bob, carol = game["students"]
    r = await client.post(f"/worlds/{wid}/compacts", headers=hdr(alice["token"]),
                          json={"name": "The Wool Ring", "kind": "price_accord",
                                "terms": {"good": "wool", "price": 50}})
    cid = r.json()["compact_id"]
    await client.post(f"/worlds/{wid}/compacts/{cid}/join", headers=hdr(bob["token"]))
    r = await client.get(f"/worlds/{wid}/compacts", headers=hdr(carol["token"]))
    ring = r.json()[0]
    assert len(ring["members"]) == 2 and ring["terms"]["good"] == "wool"
    # members sell wool at the accord price; carol buys; detector should flag
    for member in (alice, bob):
        await client.post(f"/worlds/{wid}/gather", headers=hdr(member["token"]),
                          json={"good_id": "wool", "effort": 6})
        for _ in range(2):  # several separate asks -> several member trades
            await client.post(f"/worlds/{wid}/orders", headers=hdr(member["token"]),
                              json={"good_id": "wool", "side": "sell", "qty": 1, "price": 50})
    await client.post(f"/worlds/{wid}/orders", headers=hdr(carol["token"]),
                      json={"good_id": "wool", "side": "buy", "qty": 4, "price": 50})
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    r = await client.get(f"/worlds/{wid}/instructor/feed", headers=hdr(prof["token"]))
    kinds = {m["kind"] for m in r.json()["moments"]}
    assert "cartel_parallel_pricing" in kinds
    # defection: bob leaves and undercuts
    r = await client.post(f"/worlds/{wid}/compacts/{cid}/leave", headers=hdr(bob["token"]))
    assert r.status_code == 200


async def test_smog_tax_and_scrubber(game):
    client = game["client"]
    wid = await advance_to_week(client, game, 6)
    prof, alice = game["instructor"], game["students"][0]
    sf = game["session_factory"]
    # give alice a smelter + ore so production emits smog
    import uuid as _uuid

    from sqlalchemy import select, update

    from app.models import Facility, Inventory, Player

    async with sf() as db:
        async with db.begin():
            player = await db.scalar(select(Player).where(
                Player.world_id == _uuid.UUID(wid), Player.merchant_name == "Student 0"))
            db.add(Facility(world_id=_uuid.UUID(wid), player_id=player.id,
                            kind="smelter", tier=1))
            db.add(Inventory(world_id=_uuid.UUID(wid), player_id=player.id,
                             good_id="ore", qty=50))
            player.coins = 1000
    await client.post(f"/worlds/{wid}/instructor/interventions", headers=hdr(prof["token"]),
                      json={"kind": "smog_tax", "params": {"per_unit": 3}})
    r = await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["world"]["smog"] is not None
    # smelter: 4 output * 3 smog = 12 emissions; coins: -upkeep(4) -tax(36) +nothing sold
    assert state["player"]["coins"] < 1000
    facs = state["facilities"]
    fid = facs[0]["id"]
    r = await client.post(f"/worlds/{wid}/facilities/{fid}/scrubber", headers=hdr(alice["token"]))
    assert r.status_code == 200 and r.json()["scrubber"]


async def test_fresh_start_loan(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.post(f"/worlds/{wid}/fresh-start", headers=hdr(alice["token"]))
    assert r.status_code == 400  # not broke yet
    # go broke buying
    r = await client.post(f"/worlds/{wid}/orders", headers=hdr(alice["token"]),
                          json={"good_id": "grain", "side": "buy", "qty": 4, "price": 45})
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 20
    r = await client.post(f"/worlds/{wid}/fresh-start", headers=hdr(alice["token"]))
    assert r.status_code == 200
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(alice["token"]))).json()
    assert state["player"]["coins"] == 140 and state["loan"]["outstanding"] == 120


async def test_boutique_coin_sink(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.get(f"/worlds/{wid}/boutique", headers=hdr(alice["token"]))
    assert "awning_striped" in r.json()
    r = await client.post(f"/worlds/{wid}/boutique/buy", headers=hdr(alice["token"]),
                          json={"cosmetic_id": "awning_striped"})
    assert r.json()["coins"] == 120
    r = await client.post(f"/worlds/{wid}/boutique/buy", headers=hdr(alice["token"]),
                          json={"cosmetic_id": "awning_striped"})
    assert r.status_code == 400  # no double-buys


async def test_playbook_and_recap(game):
    client = game["client"]
    wid = await advance_to_week(client, game, 7)
    prof, alice = game["instructor"], game["students"][0]
    await client.post(f"/worlds/{wid}/instructor/close-day", headers=hdr(prof["token"]))
    r = await client.get(f"/worlds/{wid}/instructor/playbook", headers=hdr(prof["token"]))
    pb = r.json()
    assert pb["week"] == 7 and "markdown" in pb and "Lecture Playbook" in pb["markdown"]
    r = await client.post(f"/worlds/{wid}/instructor/state", headers=hdr(prof["token"]),
                          json={"state": "epilogue"})
    r = await client.get(f"/worlds/{wid}/recap", headers=hdr(alice["token"]))
    recap = r.json()
    assert recap["merchant"] == "Student 0" and "chapters" in recap


async def test_puzzle_ignores_legacy_number_guesses(game):
    """Rows written by the retired price-guessing game (ints) must not break
    the Connections view if a deploy lands mid-day."""
    import uuid as _uuid

    from app.models import PuzzleAttempt, World

    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    async with game["session_factory"]() as db:
        async with db.begin():
            world = await db.get(World, _uuid.UUID(wid))
            db.add(PuzzleAttempt(world_id=world.id,
                                 player_id=_uuid.UUID(alice["player_id"]),
                                 world_day=world.world_day,
                                 guesses=[54, 62, 71]))
    r = await client.get(f"/worlds/{wid}/puzzle", headers=hdr(alice["token"]))
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["mistakes_left"] == 4 and p["found"] == [] and not p["finished"]
    key = await _todays_puzzle(game)
    r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(alice["token"]),
                          json={"terms": key["groups"][0]["terms"]})
    assert r.status_code == 200 and r.json()["result"] == "correct"


def _bank_answer(question_id: str) -> str:
    """A correct answer for any bank question (keyword fallback grades free text)."""
    from app.pedagogy.bank import QUESTIONS

    q = QUESTIONS[question_id]
    return str(q.answer) if q.kind == "mcq" else " ".join(q.keywords)


async def test_practice_targets_objective_and_never_runs_dry(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    for _ in range(6):  # more rounds than the LO has questions
        r = await client.get(f"/worlds/{wid}/tutor/check?lo=ch3-equilibrium",
                             headers=hdr(alice["token"]))
        q = r.json()
        assert "question_id" in q, q
        assert "ch3-equilibrium" in q["lo_ids"]
        r = await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(alice["token"]),
                              json={"question_id": q["question_id"],
                                    "answer": _bank_answer(q["question_id"])})
        assert r.status_code == 200
    # mastery is now visible to the student, scored and attempted
    r = await client.get(f"/worlds/{wid}/tutor/mastery", headers=hdr(alice["token"]))
    row = next(m for m in r.json() if m["lo_id"] == "ch3-equilibrium")
    assert row["pct"] is not None and row["attempts"] >= 6
    r = await client.get(f"/worlds/{wid}/tutor/check?lo=not-a-real-lo",
                         headers=hdr(alice["token"]))
    assert r.status_code == 400


async def test_diagram_questions_well_formed():
    from app.pedagogy.bank import LEARNING_OBJECTIVES, QUESTIONS

    diag = [q for q in QUESTIONS.values() if q.diagram]
    assert len(diag) >= 10
    for q in diag:
        assert q.kind == "mcq" and 0 <= q.answer < len(q.choices)
        assert all(lo in LEARNING_OBJECTIVES for lo in q.los)
        for line in q.diagram["lines"]:
            assert line["color"] in ("sage", "terracotta", "sky", "ink")
            for x, y in line["pts"]:
                assert 0 <= x <= 100 and 0 <= y <= 100


async def test_first_correct_check_of_day_pays_effort(game):
    client, wid = game["client"], game["world_id"]
    bob = game["students"][1]
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(bob["token"]))).json()
    effort0 = state["player"]["effort"]
    r = await client.get(f"/worlds/{wid}/tutor/check?lo=ch3-shortage-surplus",
                         headers=hdr(bob["token"]))
    q = r.json()
    out = (await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(bob["token"]),
                             json={"question_id": q["question_id"],
                                   "answer": _bank_answer(q["question_id"])})).json()
    assert out["correct"] and out["effort_gained"] == 2
    r = await client.get(f"/worlds/{wid}/tutor/check?lo=ch3-shortage-surplus",
                         headers=hdr(bob["token"]))
    q2 = r.json()
    out2 = (await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(bob["token"]),
                              json={"question_id": q2["question_id"],
                                    "answer": _bank_answer(q2["question_id"])})).json()
    assert out2["correct"] and out2["effort_gained"] == 0
    state = (await client.get(f"/worlds/{wid}/state", headers=hdr(bob["token"]))).json()
    assert state["player"]["effort"] == min(40, effort0 + 2)


def test_generated_question_parsing():
    from app.pedagogy.tutor import _parse_generated

    good = ('Noise before {"prompt": "P?", "choices": ["a", "b", "c", "d"], '
            '"answer": 2, "explanation": "Coo."} and after')
    parsed = _parse_generated(good)
    assert parsed and parsed["answer"] == 2 and len(parsed["choices"]) == 4
    assert _parse_generated("no json here") is None
    assert _parse_generated('{"prompt": "P", "choices": ["a","b","c"], "answer": 0}') is None
    assert _parse_generated('{"prompt": "P", "choices": ["a","a","b","c"], "answer": 0}') is None
    assert _parse_generated('{"prompt": "P", "choices": ["a","b","c","d"], "answer": 7}') is None
    assert _parse_generated('{"prompt": "", "choices": ["a","b","c","d"], "answer": 1}') is None


async def test_generated_question_grading(game):
    import uuid as _uuid

    from app.models import GeneratedQuestion, World

    client, wid = game["client"], game["world_id"]
    alice, bob = game["students"][0], game["students"][1]
    async with game["session_factory"]() as db:
        async with db.begin():
            world = await db.get(World, _uuid.UUID(wid))
            row = GeneratedQuestion(
                world_id=world.id, player_id=_uuid.UUID(alice["player_id"]),
                lo_id="ch3-equilibrium", world_day=world.world_day,
                prompt="Where does a market clear?",
                choices=["Where S crosses D", "At the highest price",
                         "At zero", "Wherever the Crown says"],
                answer=0, explanation="Supply meets demand and both sides agree.")
            db.add(row)
        qid = f"gen:{row.id}"
    # someone else's generated question is not answerable
    r = await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(bob["token"]),
                          json={"question_id": qid, "answer": "0"})
    assert r.status_code == 400
    # the owner answers it and mastery moves
    r = await client.post(f"/worlds/{wid}/tutor/check", headers=hdr(alice["token"]),
                          json={"question_id": qid, "answer": "0"})
    out = r.json()
    assert out["correct"] and "Supply meets demand" in out["feedback"]
    r = await client.get(f"/worlds/{wid}/tutor/mastery", headers=hdr(alice["token"]))
    row_m = next(m for m in r.json() if m["lo_id"] == "ch3-equilibrium")
    assert row_m["pct"] is not None and row_m["attempts"] >= 1


async def test_bank_depth_and_lo_rigor():
    from collections import Counter

    from app.pedagogy.bank import LEARNING_OBJECTIVES, QUESTIONS
    from app.pedagogy.openstax import CHAPTER_SUMMARIES

    counts = Counter()
    for q in QUESTIONS.values():
        for lo in q.los:
            counts[lo] += 1
    for lo in LEARNING_OBJECTIVES.values():
        assert counts[lo.id] >= 5, f"{lo.id} has only {counts[lo.id]} questions"
        assert lo.short and len(lo.short) <= 24
        assert lo.bloom in ("Remember", "Understand", "Apply", "Analyze",
                            "Evaluate", "Create")
        assert len(lo.text) > 60, f"{lo.id} objective reads too thin"
        assert lo.chapter in CHAPTER_SUMMARIES, f"{lo.id} lacks textbook grounding"
    assert len(QUESTIONS) >= 130


async def test_gradebook_csv_defuses_formula_injection(game, session_factory):
    import uuid as _uuid

    from sqlalchemy import update

    from app.models import Player

    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    # a student whose display name is a spreadsheet formula
    async with session_factory() as db:
        async with db.begin():
            await db.execute(update(Player).where(
                Player.id == _uuid.UUID(alice["player_id"])).values(
                merchant_name="=cmd|'/c calc'!A1"))
    r = await client.get(f"/worlds/{wid}/instructor/gradebook.csv",
                         headers=hdr(prof["token"]))
    assert r.status_code == 200
    # the dangerous cell is present but neutralized with a leading quote
    assert "'=cmd|'/c calc'!A1" in r.text
    for line in r.text.splitlines():
        for cell in line.split(","):
            assert not cell.lstrip('"').startswith(("=", "+", "@")), cell

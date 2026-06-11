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


async def test_puzzle_full_arc(game):
    client, wid = game["client"], game["world_id"]
    alice = game["students"][0]
    r = await client.get(f"/worlds/{wid}/puzzle", headers=hdr(alice["token"]))
    puzzle = r.json()
    assert puzzle["max_guesses"] == 6 and not puzzle["finished"]
    # the heat feedback (scalding<=3, warm<=10, cold>10) makes 6 guesses enough
    lo, hi = 10, 99
    solved = False
    for _ in range(6):
        guess = (lo + hi) // 2
        r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(alice["token"]),
                              json={"guess": guess})
        out = r.json()
        if out["solved"]:
            solved = True
            break
        direction, heat = out["feedback"].split(":")
        if direction == "higher":
            lo = guess + 1
            if heat == "scalding":
                hi = min(hi, guess + 3)
            elif heat == "warm":
                lo, hi = max(lo, guess + 4), min(hi, guess + 10)
            else:
                lo = max(lo, guess + 11)
        else:
            hi = guess - 1
            if heat == "scalding":
                lo = max(lo, guess - 3)
            elif heat == "warm":
                lo, hi = max(lo, guess - 10), min(hi, guess - 4)
            else:
                hi = min(hi, guess - 11)
    assert solved, "heat-guided search must crack a 10-99 secret in <=6 guesses"
    r = await client.post(f"/worlds/{wid}/puzzle/guess", headers=hdr(alice["token"]),
                          json={"guess": 50})
    assert r.status_code == 400  # closed for the day


async def test_fishing_and_quota(game):
    client, wid = game["client"], game["world_id"]
    prof, alice = game["instructor"], game["students"][0]
    caught = 0
    for _ in range(5):
        r = await client.post(f"/worlds/{wid}/fishing/cast", headers=hdr(alice["token"]))
        assert r.status_code == 200
        caught += r.json()["qty"]
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
    r = await client.post(f"/worlds/{wid}/merchant/submit", headers=hdr(alice["token"]),
                          json={"legs": legs})
    assert r.status_code == 400  # one run only


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

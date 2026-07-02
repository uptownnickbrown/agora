"""The Fun Layer: the daily puzzle, fishing, the Traveling Merchant, the
haggling caravan, streaks, achievements, cosmetics (spec §7).
Small, deliberate, important.
"""
from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    FishingCatch,
    HaggleSession,
    MerchantRun,
    Player,
    PlayerAchievement,
    PlayerCosmetic,
    PuzzleAttempt,
    Streak,
    World,
)
from ..puzzles import PUZZLES
from .common import GameError, adjust_coins, adjust_goods, emit, spend_effort

# -- Common Threads (the Daily Ledger puzzle) ---------------------------------
#
# Connections-style: sixteen terms, four hidden groups of four, four mistakes.
# One puzzle per world day, the same for the whole class — a shared object to
# argue about. Guesses are stored as lists of terms, so a correct group is any
# stored guess that exactly matches one of today's groups.

MAX_MISTAKES = 4
PUZZLE_REWARD_EFFORT = 2
PUZZLE_FLAWLESS_BONUS = 1


def puzzle_of_the_day(world: World) -> dict:
    # Each world walks the bank from a seeded starting point, one per day.
    start = random.Random(f"puzzle-cycle:{world.id}").randrange(len(PUZZLES))
    spec = PUZZLES[(start + world.world_day) % len(PUZZLES)]
    groups = [{"name": name, "terms": terms, "tier": tier}
              for tier, (name, terms) in enumerate(spec)]
    terms = [t for g in groups for t in g["terms"]]
    # The board layout is shared too (seeded by world + day, not player).
    random.Random(f"puzzle:{world.id}:{world.world_day}").shuffle(terms)
    return {"groups": groups, "terms": terms}


def _match_group(groups: list[dict], guess: list[str]) -> dict | None:
    gset = {t.lower() for t in guess}
    for g in groups:
        if {t.lower() for t in g["terms"]} == gset:
            return g
    return None


def _puzzle_view(p: dict, attempt: PuzzleAttempt | None) -> dict:
    # Ignore rows from the retired number-guessing game (ints, not term lists)
    # so a mid-day deploy can't strand anyone who already played.
    guesses: list[list[str]] = [g for g in (attempt.guesses if attempt else [])
                                if isinstance(g, list)]
    found = [g for g in (_match_group(p["groups"], guess) for guess in guesses) if g]
    mistakes = len(guesses) - len(found)
    tier_of = {t.lower(): g["tier"] for g in p["groups"] for t in g["terms"]}
    return {
        "guesses": guesses,
        "guess_tiers": [[tier_of[t.lower()] for t in guess] for guess in guesses],
        "found": found,
        "mistakes_left": MAX_MISTAKES - mistakes,
    }


async def _attempt_today(db: AsyncSession, world: World, player: Player) -> PuzzleAttempt | None:
    return await db.scalar(
        select(PuzzleAttempt).where(
            PuzzleAttempt.world_id == world.id,
            PuzzleAttempt.player_id == player.id,
            PuzzleAttempt.world_day == world.world_day,
        )
    )


async def get_puzzle_state(db: AsyncSession, world: World, player: Player) -> dict:
    p = puzzle_of_the_day(world)
    attempt = await _attempt_today(db, world, player)
    view = _puzzle_view(p, attempt)
    streak = await db.scalar(
        select(Streak).where(Streak.player_id == player.id, Streak.kind == "puzzle")
    )
    finished = bool(attempt and attempt.finished)
    # A streak that skipped a day is over — show it as such.
    alive = bool(streak and streak.last_day >= world.world_day - 1)
    return {
        "day": world.world_day,
        "terms": p["terms"],
        "found": view["found"],
        "guesses": view["guesses"],
        "guess_tiers": view["guess_tiers"],
        "mistakes_left": view["mistakes_left"],
        "max_mistakes": MAX_MISTAKES,
        "solved": bool(attempt and attempt.solved),
        "finished": finished,
        "reveal": p["groups"] if finished else None,
        "streak": streak.count if alive else 0,
        "streak_best": streak.best if streak else 0,
        "reward_effort": PUZZLE_REWARD_EFFORT,
        "flawless_bonus": PUZZLE_FLAWLESS_BONUS,
    }


async def guess_puzzle(db: AsyncSession, world: World, player: Player,
                       terms: list[str]) -> dict:
    p = puzzle_of_the_day(world)
    valid = {t.lower() for t in p["terms"]}
    guess = [t for t in terms]
    if len(guess) != 4 or len({t.lower() for t in guess}) != 4:
        raise GameError("pick exactly four different terms")
    if not all(t.lower() in valid for t in guess):
        raise GameError("those terms are not on today's board")

    attempt = await _attempt_today(db, world, player)
    if attempt is None:
        attempt = PuzzleAttempt(world_id=world.id, player_id=player.id,
                                world_day=world.world_day, guesses=[])
        db.add(attempt)
        await db.flush()
    if attempt.finished:
        raise GameError("today's ledger is closed — come back tomorrow")

    view = _puzzle_view(p, attempt)
    gset = {t.lower() for t in guess}
    found_terms = {t.lower() for g in view["found"] for t in g["terms"]}
    if gset & found_terms:
        raise GameError("some of those are already solved")
    if any(isinstance(old, list) and {t.lower() for t in old} == gset
           for old in attempt.guesses):
        return {"result": "already_guessed", "mistakes_left": view["mistakes_left"],
                "solved": False, "finished": False, "effort_gained": 0}

    attempt.guesses = list(attempt.guesses) + [guess]
    group = _match_group(p["groups"], guess)
    effort_gained = 0
    one_away = False
    if group:
        solved = len(_puzzle_view(p, attempt)["found"]) == 4
        if solved:
            attempt.solved = True
            attempt.finished = True
            await _bump_streak(db, world, player, "puzzle")
            mistakes = len(attempt.guesses) - 4
            effort_gained = PUZZLE_REWARD_EFFORT + (
                PUZZLE_FLAWLESS_BONUS if mistakes == 0 else 0)
            player.effort = min(T.BALANCE["effort_cap"], player.effort + effort_gained)
            await emit(db, world, "puzzle_solved",
                       {"mistakes": mistakes, "effort": effort_gained}, actor=player.id)
    else:
        one_away = any(
            len(gset & {t.lower() for t in g["terms"]}) == 3 for g in p["groups"])
        if _puzzle_view(p, attempt)["mistakes_left"] <= 0:
            attempt.finished = True
            await emit(db, world, "puzzle_failed", {}, actor=player.id)

    player.last_active_day = world.world_day
    view = _puzzle_view(p, attempt)
    return {
        "result": "correct" if group else "one_away" if one_away else "wrong",
        "group": group,
        "mistakes_left": view["mistakes_left"],
        "solved": attempt.solved,
        "finished": attempt.finished,
        "reveal": p["groups"] if attempt.finished else None,
        "effort_gained": effort_gained,
    }


# -- Fishing at the Docks -------------------------------------------------------

# (roll floor out of 10,000, trophy name) — checked in order, rarest first.
TROPHIES = [
    (9920, "The Gilded Leviathan"),
    (9600, "Old Whiskerjaw"),
    (8800, "A Remarkably Smug Trout"),
]

# Species by single-fish weight (decigrams): flavor for the reveal.
SPECIES = [
    (250, "Copper Minnow"),
    (400, "Reedgill"),
    (550, "Marketday Perch"),
    (700, "Ledger Carp"),
    (850, "Saltharbor Bream"),
    (1000, "Moonlit Pike"),
]

MISS_FLAVOR = [
    "The hook comes back bare. The fish send their regards.",
    "A boot. A remarkably old boot. You throw it back.",
    "Seaweed. Philosophically interesting seaweed.",
    "Something enormous inspects your bait, and declines.",
    "A single indignant bubble surfaces. Nothing else.",
]


def _species_of(weight_dg: int) -> str:
    for cap, name in SPECIES:
        if weight_dg <= cap:
            return name
    return SPECIES[-1][1]


def _size_class(weight_dg: int) -> str:
    return "minnow" if weight_dg < 300 else "keeper" if weight_dg < 700 else "prize"


def fish_capacity(world: World) -> int:
    return (world.config or {}).get("fish_capacity", T.BALANCE["fish_capacity"])


async def cast_line(db: AsyncSession, world: World, player: Player) -> dict:
    rules = world.fishing_rules or {}
    if rules.get("closed"):
        raise GameError("the fishery is closed by royal order")
    quota = rules.get("quota")
    if quota is not None:
        caught_today = await db.scalar(
            select(func.coalesce(func.sum(FishingCatch.fish_qty), 0)).where(
                FishingCatch.world_id == world.id,
                FishingCatch.player_id == player.id,
                FishingCatch.world_day == world.world_day,
            )
        )
        if caught_today >= quota:
            raise GameError(f"royal quota reached ({quota}/day)")
    prev_best = await db.scalar(
        select(func.coalesce(func.max(FishingCatch.weight), 0)).where(
            FishingCatch.player_id == player.id)
    )
    spend_effort(player, T.BALANCE["fishing_effort_cost"])
    # Deterministic per world/player/day/cast: reproducible sims, no rerolls.
    rng = random.Random(f"cast:{world.id}:{player.id}:{world.world_day}:{player.effort}")
    stock_ratio = world.fish_stock / max(1, fish_capacity(world))
    # Catch scales with stock: a depleted commons yields nothing (Week 6).
    roll = rng.random()
    qty = 0
    if roll < stock_ratio * 0.95:
        qty = 1 + (1 if rng.random() < stock_ratio * 0.6 else 0) + (
            1 if rng.random() < stock_ratio * 0.3 else 0
        )
    if quota is not None and qty > 0:
        qty = min(qty, quota)
    fish: list[dict] = []
    weight = 0
    trophy = None
    if qty:
        for _ in range(qty):
            w = rng.randint(5, 100) * 10
            fish.append({"species": _species_of(w), "weight": w,
                         "size_class": _size_class(w)})
        weight = sum(f["weight"] for f in fish)
        troll = rng.randint(0, 9999)
        for threshold, name in TROPHIES:
            if troll >= threshold:
                trophy = name
                break
        world.fish_stock = max(0, world.fish_stock - qty)
        await adjust_goods(db, world.id, player, "fish", qty)
    catch = FishingCatch(world_id=world.id, player_id=player.id, world_day=world.world_day,
                         fish_qty=qty, weight=weight, trophy=trophy)
    db.add(catch)
    if trophy:
        await _award(db, world, player, f"trophy:{trophy}")
    player.last_active_day = world.world_day
    await emit(db, world, "fishing_cast", {"qty": qty, "weight": weight, "trophy": trophy},
               actor=player.id)
    return {
        "qty": qty,
        "weight": weight,
        "fish": fish,
        "trophy": trophy,
        # Choreography hints for the client: when the bite comes, how many
        # false nibbles first. Pure theater — the outcome is already decided.
        "bite_ms": rng.randint(900, 2600),
        "nibbles": rng.randint(0, 2),
        "personal_best": bool(qty and weight > prev_best and prev_best > 0),
        "miss_flavor": None if qty else rng.choice(MISS_FLAVOR),
        "stock_hint": _stock_hint(stock_ratio),
    }


def _stock_hint(ratio: float) -> str:
    if ratio > 0.7:
        return "The water boils with fish."
    if ratio > 0.4:
        return "A decent day on the water."
    if ratio > 0.15:
        return "The casts come back light. Something is wrong out there."
    return "The water is quiet. Too quiet."


def fishery_regen(world: World) -> None:
    """Logistic regrowth at daily close — the commons can recover if allowed,
    but max regrowth (~r*cap/4 ≈ 30/day) loses to a class fishing freely."""
    cap = fish_capacity(world)
    rate = T.BALANCE["fish_regen_rate_bp"] / 10_000
    s = world.fish_stock
    world.fish_stock = min(cap, s + max(0, round(rate * s * (1 - s / cap))))


# -- The Traveling Merchant (Week 1 onboarding) ----------------------------------

MERCHANT_PORTS = ["Saltharbor", "Milltown", "The Crossroads"]
MERCHANT_GOODS = ["grain", "wool", "wood", "cloth"]
MERCHANT_CAPACITY = 10
MERCHANT_BANKROLL = 100


def _merchant_instance(seed: int) -> dict:
    rng = random.Random(f"merchant:{seed}")
    prices = {
        port: {g: max(5, round(T.GOODS[g].anchor * rng.uniform(0.5, 1.6)))
               for g in MERCHANT_GOODS}
        for port in MERCHANT_PORTS
    }
    return {"ports": MERCHANT_PORTS, "goods": MERCHANT_GOODS, "prices": prices,
            "capacity": MERCHANT_CAPACITY, "bankroll": MERCHANT_BANKROLL}


def _optimal_profit(inst: dict) -> int:
    """Best possible final coins minus bankroll. Since the only state carried
    between legs is coins, and the best a leg can do never decreases with more
    coins, maximizing coins leg by leg is globally optimal."""
    coins = inst["bankroll"]
    for i in range(len(inst["ports"]) - 1):
        cur, nxt = inst["ports"][i], inst["ports"][i + 1]
        best_end = coins
        # Enumerate allocations of up to `capacity` crates among the goods.
        def alloc(goods: list[str], cap: int, spend: int, revenue: int) -> None:
            nonlocal best_end
            end = coins - spend + revenue
            if end > best_end:
                best_end = end
            if not goods or cap == 0:
                return
            g, rest = goods[0], goods[1:]
            buy_p, sell_p = inst["prices"][cur][g], inst["prices"][nxt][g]
            for q in range(0, cap + 1):
                s = spend + q * buy_p
                if s > coins:
                    break
                alloc(rest, cap - q, s, revenue + q * sell_p)
        alloc(inst["goods"], inst["capacity"], 0, 0)
        coins = best_end
    return coins - inst["bankroll"]


async def merchant_state(db: AsyncSession, world: World, player: Player) -> dict:
    run = await db.scalar(
        select(MerchantRun).where(MerchantRun.world_id == world.id,
                                  MerchantRun.player_id == player.id)
    )
    if run is None:
        run = MerchantRun(world_id=world.id, player_id=player.id,
                          seed=random.Random(str(player.id)).randint(0, 2**30))
        db.add(run)
        await db.flush()
    inst = _merchant_instance(run.seed)
    out = {**inst, "completed": run.completed, "profit": run.profit}
    if run.completed:
        best = _optimal_profit(inst)
        out["best_profit"] = best
        out["pct_of_best"] = round(100 * run.profit / best) if best > 0 else 100
    return out


async def merchant_submit(db: AsyncSession, world: World, player: Player,
                          legs: list[dict]) -> dict:
    """legs = [{"port": name, "buy": {good: qty}}, ...] in port order; cargo is
    sold automatically at the NEXT port. Comparative advantage, re-skinned."""
    run = await db.scalar(
        select(MerchantRun).where(MerchantRun.world_id == world.id,
                                  MerchantRun.player_id == player.id)
    )
    if run is None or run.completed:
        raise GameError("the Traveling Merchant has moved on")
    inst = _merchant_instance(run.seed)
    coins = inst["bankroll"]
    if len(legs) != len(inst["ports"]) - 1:
        raise GameError(f"plan exactly {len(inst['ports']) - 1} legs")
    for i, leg in enumerate(legs):
        port, next_port = inst["ports"][i], inst["ports"][i + 1]
        if leg.get("port") != port:
            raise GameError(f"leg {i + 1} must start at {port}")
        buys = leg.get("buy") or {}
        total_qty = sum(buys.values())
        if total_qty > inst["capacity"]:
            raise GameError(f"cargo hold fits {inst['capacity']} crates")
        cost = 0
        for good, qty in buys.items():
            if good not in inst["goods"] or qty < 0:
                raise GameError("unknown cargo")
            cost += inst["prices"][port][good] * qty
        if cost > coins:
            raise GameError(f"not enough coin at {port} (have {coins}, need {cost})")
        coins -= cost
        for good, qty in buys.items():
            coins += inst["prices"][next_port][good] * qty
    profit = coins - inst["bankroll"]
    run.completed = True
    run.profit = profit
    reward = max(20, min(T.BALANCE["merchant_reward_cap"], profit))
    adjust_coins(player, reward)
    await _award(db, world, player, "traveling_merchant")
    await emit(db, world, "merchant_completed", {"profit": profit, "reward": reward},
               actor=player.id)
    best = _optimal_profit(inst)
    return {"profit": profit, "reward": reward, "best_profit": best,
            "pct_of_best": round(100 * profit / best) if best > 0 else 100}


# -- The haggling caravan ---------------------------------------------------------
#
# One visitor a day, per merchant. They name a good and a quantity; you name a
# price per unit; their true limit stays hidden until the deal closes. Consumer
# and producer surplus, taught by an old woman who will absolutely walk away.

HAGGLE_MAX_OFFERS = 3

VISITORS = [
    ("Mirela of the Dune Caravan", "mirela"),
    ("Old Tam the Peddler", "tam"),
    ("Brother Alms of the Abbey", "alms"),
    ("Sable the Spice Runner", "sable"),
    ("Grandmother Vex", "vex"),
]

HAGGLE_REJECTIONS = {
    "far": ["\"Ha! Do I look freshly fallen off the turnip cart?\"",
            "\"Outrageous. I've been insulted in nicer towns than this.\"",
            "\"My dear, that is not a price. That is a dare.\""],
    "close": ["\"Mm. Closer. But my purse still says no.\"",
              "\"You're circling the number. Circle faster.\"",
              "\"Almost worth shaking on. Almost.\""],
}


def _haggle_rng(world: World, player: Player) -> random.Random:
    return random.Random(f"haggle:{world.id}:{player.id}:{world.world_day}")


async def _haggle_today(db: AsyncSession, world: World, player: Player) -> HaggleSession | None:
    return await db.scalar(
        select(HaggleSession).where(
            HaggleSession.world_id == world.id,
            HaggleSession.player_id == player.id,
            HaggleSession.world_day == world.world_day,
        )
    )


async def haggle_state(db: AsyncSession, world: World, player: Player) -> dict:
    session = await _haggle_today(db, world, player)
    if session is None:
        rng = _haggle_rng(world, player)
        visitor, portrait = VISITORS[
            (world.world_day + rng.randint(0, len(VISITORS) - 1)) % len(VISITORS)]
        # The visitor buys something you hold (else sells you something useful).
        from ..models import Inventory

        held = (
            await db.execute(
                select(Inventory.good_id, Inventory.qty).where(
                    Inventory.world_id == world.id,
                    Inventory.player_id == player.id,
                    Inventory.qty >= 2,
                )
            )
        ).all()
        unlocked = [g.id for g in T.GOODS.values()
                    if g.unlock_week <= world.current_week and not g.license_required]
        sellable = sorted(g for g, _ in held if g in unlocked)
        if sellable:
            side = "npc_buys"
            good = sellable[rng.randrange(len(sellable))]
            reservation = max(5, round(T.GOODS[good].anchor * rng.uniform(1.15, 1.7)))
        else:
            side = "npc_sells"
            good = unlocked[rng.randrange(len(unlocked))]
            reservation = max(3, round(T.GOODS[good].anchor * rng.uniform(0.55, 0.95)))
        session = HaggleSession(
            world_id=world.id, player_id=player.id, world_day=world.world_day,
            good_id=good, side=side, qty=rng.randint(2, 5),
            reservation=reservation, visitor=visitor, portrait=portrait,
            offers=[], state="open",
        )
        db.add(session)
        await db.flush()
    done = session.state != "open"
    return {
        "visitor": session.visitor,
        "portrait": session.portrait,
        "side": session.side,
        "good": session.good_id,
        "qty": session.qty,
        "offers": session.offers,
        "offers_left": HAGGLE_MAX_OFFERS - len(session.offers),
        "state": session.state,
        "accepted_price": session.accepted_price,
        # The lesson: reveal their true limit only once the table clears.
        "reservation": session.reservation if done else None,
    }


async def haggle_offer(db: AsyncSession, world: World, player: Player, price: int) -> dict:
    session = await _haggle_today(db, world, player)
    if session is None or session.state != "open":
        raise GameError("no open deal — the caravan returns tomorrow")
    if price <= 0:
        raise GameError("name a real price")
    rng = random.Random(
        f"haggle-offer:{world.id}:{player.id}:{world.world_day}:{len(session.offers)}")
    session.offers = list(session.offers) + [price]
    # The player quotes a per-unit price. A buying visitor accepts any quote at
    # or under their hidden ceiling; a selling visitor, at or over their floor.
    accepted = (price <= session.reservation if session.side == "npc_buys"
                else price >= session.reservation)
    if accepted:
        total = price * session.qty
        if session.side == "npc_buys":
            await adjust_goods(db, world.id, player, session.good_id, -session.qty)
            adjust_coins(player, total)
        else:
            adjust_coins(player, -total)
            await adjust_goods(db, world.id, player, session.good_id, session.qty)
        session.state = "accepted"
        session.accepted_price = price
        left_on_table = abs(session.reservation - price) * session.qty
        if left_on_table <= max(1, round(0.05 * session.reservation)) * session.qty:
            await _award(db, world, player, "silver_tongue")
        await emit(db, world, "haggle_closed",
                   {"good": session.good_id, "qty": session.qty, "price": price,
                    "side": session.side}, actor=player.id)
        player.last_active_day = world.world_day
        return {"result": "accepted", "price": price, "qty": session.qty,
                "total": total if session.side == "npc_buys" else -total,
                "reservation": session.reservation,
                "left_on_table": left_on_table,
                "offers_left": HAGGLE_MAX_OFFERS - len(session.offers)}
    # Rejected: flavor scales with how far off the quote was.
    gap = abs(price - session.reservation) / max(1, session.reservation)
    flavor = rng.choice(HAGGLE_REJECTIONS["close" if gap <= 0.15 else "far"])
    walked = len(session.offers) >= HAGGLE_MAX_OFFERS
    if walked:
        session.state = "walked"
        await emit(db, world, "haggle_walked", {"good": session.good_id},
                   actor=player.id)
    player.last_active_day = world.world_day
    return {"result": "walked" if walked else "rejected", "flavor": flavor,
            "hint": "close" if gap <= 0.15 else "far",
            "offers_left": HAGGLE_MAX_OFFERS - len(session.offers),
            "reservation": session.reservation if walked else None}


async def haggle_walk(db: AsyncSession, world: World, player: Player) -> dict:
    session = await _haggle_today(db, world, player)
    if session is None or session.state != "open":
        raise GameError("no open deal — the caravan returns tomorrow")
    session.state = "declined"
    await emit(db, world, "haggle_declined", {"good": session.good_id}, actor=player.id)
    return {"result": "declined", "reservation": session.reservation}


# -- streaks, achievements, cosmetics ---------------------------------------------

async def _bump_streak(db: AsyncSession, world: World, player: Player, kind: str) -> Streak | None:
    streak = await db.scalar(
        select(Streak).where(Streak.player_id == player.id, Streak.kind == kind)
    )
    if streak is None:
        streak = Streak(world_id=world.id, player_id=player.id, kind=kind,
                        count=0, best=0, last_day=-99)
        db.add(streak)
        await db.flush()
    if streak.last_day == world.world_day:
        return None
    streak.count = streak.count + 1 if streak.last_day == world.world_day - 1 else 1
    streak.best = max(streak.best, streak.count)
    streak.last_day = world.world_day
    return streak


ACHIEVEMENTS = {
    "traveling_merchant": "Saw the World",
    "first_trade": "Open for Business",
    "cloth_baron": "Cloth Baron",
    "master_angler": "Master Angler",
    "survived_drought": "Survived the Drought",
    "arbitrage_artist": "Arbitrage Artist",
    "monopolist": "By Royal Appointment",
    "puzzle_week": "Ledger Sage",
    "silver_tongue": "Silver Tongue",
}


def achievement_name(achievement_id: str) -> str:
    if achievement_id.startswith("trophy:"):
        return achievement_id[7:]
    return ACHIEVEMENTS.get(achievement_id, achievement_id.replace("_", " ").title())


COSMETICS = {
    # earned (prestige) — achievement_id -> cosmetic
    "earned": {
        "traveling_merchant": {"id": "hat_wayfarer", "name": "Wayfarer's Hat"},
        "master_angler": {"id": "rod_gilded", "name": "Gilded Rod"},
        "monopolist": {"id": "cloak_royal", "name": "Royal Charter Cloak"},
        "puzzle_week": {"id": "quill_sage", "name": "Sage's Quill"},
    },
    # boutique (coin sink, DECISIONS.md #10)
    "boutique": {
        "awning_striped": {"name": "Striped Awning", "price": 80},
        "sign_gilt": {"name": "Gilt Shop Sign", "price": 150},
        "fountain_small": {"name": "Courtyard Fountain", "price": 400},
        "peacock": {"name": "A Live Peacock", "price": 900},
    },
}


async def _award(db: AsyncSession, world: World, player: Player, achievement_id: str) -> None:
    exists = await db.scalar(
        select(PlayerAchievement).where(
            PlayerAchievement.player_id == player.id,
            PlayerAchievement.achievement_id == achievement_id,
        )
    )
    if exists:
        return
    db.add(PlayerAchievement(world_id=world.id, player_id=player.id,
                             achievement_id=achievement_id, world_day=world.world_day))
    cosmetic = COSMETICS["earned"].get(achievement_id)
    if cosmetic:
        db.add(PlayerCosmetic(world_id=world.id, player_id=player.id,
                              cosmetic_id=cosmetic["id"]))
    await emit(db, world, "achievement", {"id": achievement_id}, actor=player.id)


async def award(db, world, player, achievement_id):
    await _award(db, world, player, achievement_id)


async def buy_cosmetic(db: AsyncSession, world: World, player: Player, cosmetic_id: str) -> None:
    item = COSMETICS["boutique"].get(cosmetic_id)
    if item is None:
        raise GameError("the Boutique does not stock that")
    owned = await db.scalar(
        select(PlayerCosmetic).where(PlayerCosmetic.player_id == player.id,
                                     PlayerCosmetic.cosmetic_id == cosmetic_id)
    )
    if owned:
        raise GameError("you already own that")
    adjust_coins(player, -item["price"])  # the coin sink doing its quiet work
    db.add(PlayerCosmetic(world_id=world.id, player_id=player.id, cosmetic_id=cosmetic_id))
    await emit(db, world, "cosmetic_bought", {"id": cosmetic_id, "price": item["price"]},
               actor=player.id)


# -- the daily streak chest ---------------------------------------------------------

def _daily_bonus_coins(streak_count: int) -> int:
    return min(25, 5 + 3 * streak_count)


async def login_streak(db: AsyncSession, world: World, player: Player) -> dict | None:
    """First visit of each world day: bump the login streak, and from the
    second consecutive day onward hand over a small coin bonus that grows with
    the streak. Returns the grant (once) so the UI can make a moment of it."""
    bumped = await _bump_streak(db, world, player, "login")
    if bumped is None or bumped.count < 2:
        return None
    coins = _daily_bonus_coins(bumped.count)
    adjust_coins(player, coins)
    await emit(db, world, "daily_bonus", {"streak": bumped.count, "coins": coins},
               actor=player.id)
    return {"streak": bumped.count, "coins": coins}

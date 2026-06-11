"""The Fun Layer: daily puzzle, fishing, the Traveling Merchant, streaks,
achievements, cosmetics (spec §7). Small, deliberate, important.
"""
from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    FishingCatch,
    MerchantRun,
    Player,
    PlayerAchievement,
    PlayerCosmetic,
    PuzzleAttempt,
    Streak,
    World,
)
from .common import GameError, adjust_coins, adjust_goods, emit, spend_effort

# -- Daily Ledger Puzzle: "Market Mastermind" ---------------------------------

PUZZLE_GOODS = ["grain", "wool", "bread", "garments", "cloth", "tools"]
MAX_GUESSES = 6

CLUE_TEMPLATES = [
    "A bumper season has flooded the market — supply sits heavy on the stalls.",
    "Caravans were waylaid this week; supply runs thin and tempers short.",
    "A fashion among the gentry has buyers elbowing for position.",
    "The town's purses are light; demand drags its feet.",
    "Rumor says the Guild has been quietly buying. Make of that what you will.",
]


def _puzzle_rng(world: World) -> random.Random:
    return random.Random(f"puzzle:{world.id}:{world.world_day}")


def puzzle_of_the_day(world: World) -> dict:
    rng = _puzzle_rng(world)
    good = rng.choice(PUZZLE_GOODS)
    secret = rng.randint(10, 99)
    clue = rng.choice(CLUE_TEMPLATES)
    return {"good": good, "secret": secret, "clue": clue}


async def get_puzzle_state(db: AsyncSession, world: World, player: Player) -> dict:
    p = puzzle_of_the_day(world)
    attempt = await db.scalar(
        select(PuzzleAttempt).where(
            PuzzleAttempt.world_id == world.id,
            PuzzleAttempt.player_id == player.id,
            PuzzleAttempt.world_day == world.world_day,
        )
    )
    guesses = attempt.guesses if attempt else []
    return {
        "day": world.world_day,
        "good": p["good"],
        "clue": p["clue"],
        "guesses": guesses,
        "feedback": [_feedback(g, p["secret"]) for g in guesses],
        "solved": bool(attempt and attempt.solved),
        "finished": bool(attempt and attempt.finished),
        "max_guesses": MAX_GUESSES,
    }


def _feedback(guess: int, secret: int) -> str:
    if guess == secret:
        return "correct"
    diff = abs(guess - secret)
    direction = "higher" if secret > guess else "lower"
    heat = "scalding" if diff <= 3 else "warm" if diff <= 10 else "cold"
    return f"{direction}:{heat}"


async def guess_puzzle(db: AsyncSession, world: World, player: Player, guess: int) -> dict:
    if not (10 <= guess <= 99):
        raise GameError("guesses are prices from 10 to 99")
    p = puzzle_of_the_day(world)
    attempt = await db.scalar(
        select(PuzzleAttempt).where(
            PuzzleAttempt.world_id == world.id,
            PuzzleAttempt.player_id == player.id,
            PuzzleAttempt.world_day == world.world_day,
        )
    )
    if attempt is None:
        attempt = PuzzleAttempt(world_id=world.id, player_id=player.id,
                                world_day=world.world_day, guesses=[])
        db.add(attempt)
        await db.flush()
    if attempt.finished:
        raise GameError("today's ledger is closed — come back tomorrow")
    guesses = list(attempt.guesses) + [guess]
    attempt.guesses = guesses
    solved = guess == p["secret"]
    if solved:
        attempt.solved = True
        attempt.finished = True
        await _bump_streak(db, world, player, "puzzle")
        player.effort = min(T.BALANCE["effort_cap"], player.effort + 2)  # streak bonus
        await emit(db, world, "puzzle_solved", {"guesses": len(guesses)}, actor=player.id)
    elif len(guesses) >= MAX_GUESSES:
        attempt.finished = True
        await emit(db, world, "puzzle_failed", {}, actor=player.id)
    player.last_active_day = world.world_day
    return {"feedback": _feedback(guess, p["secret"]), "solved": solved,
            "finished": attempt.finished, "guesses": guesses}


# -- Fishing at the Docks -------------------------------------------------------

TROPHIES = [
    (9800, "The Gilded Leviathan"),
    (9000, "Old Whiskerjaw"),
    (7500, "A Remarkably Smug Trout"),
]


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
    spend_effort(player, T.BALANCE["fishing_effort_cost"])
    rng = random.Random()
    stock_ratio = world.fish_stock / max(1, T.BALANCE["fish_capacity"])
    # Catch scales with stock: a depleted commons yields nothing (Week 6).
    roll = rng.random()
    qty = 0
    if roll < stock_ratio * 0.95:
        qty = 1 + (1 if rng.random() < stock_ratio * 0.6 else 0) + (
            1 if rng.random() < stock_ratio * 0.3 else 0
        )
    if quota is not None and qty > 0:
        qty = min(qty, quota)
    weight = 0
    trophy = None
    if qty:
        weight = rng.randint(5, 100) * qty * 10
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
    return {"qty": qty, "weight": weight, "trophy": trophy, "stock_hint": _stock_hint(stock_ratio)}


def _stock_hint(ratio: float) -> str:
    if ratio > 0.7:
        return "The water boils with fish."
    if ratio > 0.4:
        return "A decent day on the water."
    if ratio > 0.15:
        return "The casts come back light. Something is wrong out there."
    return "The water is quiet. Too quiet."


def fishery_regen(world: World) -> None:
    """Logistic regrowth at daily close — the commons can recover if allowed."""
    cap = T.BALANCE["fish_capacity"]
    rate = T.BALANCE["fish_regen_rate_bp"] / 10_000
    s = world.fish_stock
    world.fish_stock = min(cap, s + max(0, round(rate * s * (1 - s / cap) * 4)))


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
    return {**inst, "completed": run.completed, "profit": run.profit}


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
    return {"profit": profit, "reward": reward}


# -- streaks, achievements, cosmetics ---------------------------------------------

async def _bump_streak(db: AsyncSession, world: World, player: Player, kind: str) -> None:
    streak = await db.scalar(
        select(Streak).where(Streak.player_id == player.id, Streak.kind == kind)
    )
    if streak is None:
        streak = Streak(world_id=world.id, player_id=player.id, kind=kind,
                        count=0, best=0, last_day=-99)
        db.add(streak)
        await db.flush()
    if streak.last_day == world.world_day:
        return
    streak.count = streak.count + 1 if streak.last_day == world.world_day - 1 else 1
    streak.best = max(streak.best, streak.count)
    streak.last_day = world.world_day


ACHIEVEMENTS = {
    "traveling_merchant": "Saw the World",
    "first_trade": "Open for Business",
    "cloth_baron": "Cloth Baron",
    "master_angler": "Master Angler",
    "survived_drought": "Survived the Drought",
    "arbitrage_artist": "Arbitrage Artist",
    "monopolist": "By Royal Appointment",
    "puzzle_week": "Ledger Sage",
}

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


async def login_streak(db: AsyncSession, world: World, player: Player) -> None:
    await _bump_streak(db, world, player, "login")

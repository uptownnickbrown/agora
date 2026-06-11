"""Scripted student bots for the full-semester simulation.

Personas mirror real class archetypes: traders, producers, anglers, tycoons
(license bidders), and cartelists. Bots act through the same service layer the
API uses — no shortcuts past validation, escrow, or effort scarcity.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import template as T
from app.models import Inventory, Player, World
from app.services import compacts as compacts_svc
from app.services import fun as fun_svc
from app.services import licenses as lic_svc
from app.services import market as market_svc
from app.services import production as prod_svc
from app.services import shops as shops_svc
from app.services.common import GameError


@dataclass
class Bot:
    player_id: object
    persona: str          # trader | producer | angler | tycoon | cartelist
    facility_plan: str | None = None
    has_license: bool = False
    auction: str | None = None  # which sealed-bid auction this tycoon enters
    in_cartel: bool = False
    defector: bool = False
    rng: random.Random = field(default_factory=lambda: random.Random(0))


PERSONAS = ["trader", "producer", "angler", "tycoon", "cartelist", "tycoon",
            "producer", "angler", "cartelist", "producer", "trader", "cartelist"]
FACILITY_PLANS = {"producer": ["farm", "loom", "bakery"], "tycoon": ["smelter"]}


async def _inv(db: AsyncSession, world: World, pid, good: str) -> int:
    row = await db.scalar(select(Inventory).where(
        Inventory.world_id == world.id, Inventory.player_id == pid,
        Inventory.good_id == good))
    return row.qty if row else 0


async def _close_or(db, world, good, default):
    return await market_svc.last_close(db, world, good) or default


async def _ask_price(db, world, good: str, rng) -> int:
    """Sellers take the standing bid when there is one — the harness lesson:
    anchoring asks to a stale close deadlocks a shocked market."""
    bid = await market_svc.best_bid(db, world, good)
    if bid:
        return max(2, bid)
    ref = await _close_or(db, world, good, T.GOODS[good].anchor)
    return max(2, round(ref * rng.uniform(0.9, 1.0)))


async def _try(coro):
    try:
        return await coro
    except GameError:
        return None


async def bot_day(db: AsyncSession, world: World, bot: Bot, day: int, week: int) -> None:
    player = await db.get(Player, bot.player_id)
    rng = bot.rng

    # Everyone: gather the aptitude good and sell surplus into the market.
    # (Cartelists drop day-trading in week 7 — the ring is a full-time job.)
    if player.effort >= 10 and player.aptitude_good \
            and not (bot.persona == "cartelist" and week >= 7):
        await _try(prod_svc.gather(db, world, player, player.aptitude_good, 8))
        held = await _inv(db, world, player.id, player.aptitude_good)
        if held > 10:
            anchor = T.GOODS[player.aptitude_good].anchor
            ref = await _close_or(db, world, player.aptitude_good, anchor)
            price = max(2, round(ref * rng.uniform(0.95, 1.1)))
            await _try(market_svc.place_order(db, world, player, player.aptitude_good,
                                              "sell", held - 10, price, ttl_days=2))

    if bot.persona == "producer" and week >= 2:
        plan = FACILITY_PLANS["producer"]
        from app.models import Facility

        built = (await db.scalars(select(Facility).where(
            Facility.world_id == world.id, Facility.player_id == player.id))).all()
        built_kinds = {f.kind for f in built}
        for kind in plan:
            fdef = T.FACILITIES[kind]
            if kind not in built_kinds and fdef.unlock_week <= week \
                    and player.coins > fdef.build_cost[0] + 60:
                await _try(prod_svc.build_facility(db, world, player, kind))
                break
        # buy inputs for processing facilities, sell finished output
        for kind in built_kinds:
            recipe = T.RECIPES.get(T.FACILITIES[kind].output)
            if recipe:
                for good, need in recipe.inputs.items():
                    have = await _inv(db, world, player.id, good)
                    if have < need * 6 and player.coins > 50:
                        ref = await _close_or(db, world, good, T.GOODS[good].anchor)
                        await _try(market_svc.place_order(
                            db, world, player, good, "buy", need * 6 - have,
                            max(2, round(ref * 1.1)), ttl_days=2))
        for raw, out in (("wool", "cloth"), ("cloth", "garments"),
                         ("grain", "flour"), ("flour", "bread")):
            held = await _inv(db, world, player.id, raw)
            recipe = T.RECIPES[out]
            runs = held // recipe.inputs[raw]
            if runs and recipe.unlock_week <= week:
                await _try(prod_svc.craft(db, world, player, out, min(runs, 5)))
        for good in ("bread", "cloth", "garments", "flour"):
            held = await _inv(db, world, player.id, good)
            if held >= 2:
                price = await _ask_price(db, world, good, rng)
                await _try(market_svc.place_order(
                    db, world, player, good, "sell", held - 1, price, ttl_days=2))

    if bot.persona == "angler" or (week == 6 and bot.persona in ("trader", "cartelist")):
        casts = 6 if week == 6 else 2  # week 6: everyone descends on the commons
        for _ in range(casts):
            if player.effort < T.BALANCE["fishing_effort_cost"]:
                break
            await _try(fun_svc.cast_line(db, world, player))
        fish = await _inv(db, world, player.id, "fish")
        if fish > 3:
            price = await _ask_price(db, world, "fish", rng)
            await _try(market_svc.place_order(db, world, player, "fish", "sell",
                                              fish - 2, price, ttl_days=2))

    if bot.persona == "tycoon" and week >= 4:
        from app.models import Facility

        built = {f.kind for f in (await db.scalars(select(Facility).where(
            Facility.world_id == world.id, Facility.player_id == player.id))).all()}
        for kind in ("mine", "smelter"):
            fdef = T.FACILITIES[kind]
            if kind not in built and player.coins > fdef.build_cost[0] + 80:
                await _try(prod_svc.build_facility(db, world, player, kind))
                break
        iron = await _inv(db, world, player.id, "iron")
        if iron > 1:
            ref = await _close_or(db, world, "iron", T.GOODS["iron"].anchor)
            await _try(market_svc.place_order(db, world, player, "iron", "sell",
                                              iron - 1, max(2, round(ref)), ttl_days=2))

    if bot.persona == "tycoon" and week >= 5:
        if not bot.has_license:
            bid = min(player.coins - 20, 120 + rng.randint(0, 80))
            if bid > 0 and bot.auction:
                await _try(lic_svc.submit_bid(db, world, player, bot.auction, bid))
            bot.has_license = await lic_svc.player_has_license(db, world, player.id, "glowdye")
        else:
            # monopolist production: gather inputs, craft, sell dear
            if player.effort >= 10:
                await _try(prod_svc.gather(db, world, player, "herbs", 4))
                await _try(prod_svc.gather(db, world, player, "ore", 4))
            herbs = await _inv(db, world, player.id, "herbs")
            ore = await _inv(db, world, player.id, "ore")
            runs = min(herbs // 2, ore, 2)
            if runs and player.effort >= 4 * runs:
                await _try(prod_svc.craft(db, world, player, "glowdye", runs))
            dye = await _inv(db, world, player.id, "glowdye")
            if dye:
                ref = await _close_or(db, world, "glowdye", 600)
                holders = await _count_license_holders(db, world)
                # entry pressure: more rivals -> undercut harder
                price = max(150, round(ref * (1.0 - 0.06 * max(0, holders - 1))
                                       * rng.uniform(0.96, 1.02)))
                await _try(market_svc.place_order(db, world, player, "glowdye",
                                                  "sell", dye, price, ttl_days=2))

    if bot.persona == "cartelist" and week >= 7:
        if player.effort >= 10:
            await _try(prod_svc.gather(db, world, player, "wool", 6))
        wool = await _inv(db, world, player.id, "wool")
        runs = min(wool // 2, player.effort // 2, 4)
        if runs:
            await _try(prod_svc.craft(db, world, player, "cloth", runs))
        cloth = await _inv(db, world, player.id, "cloth")
        gruns = min(cloth // 2, player.effort // 2, 2)
        if gruns:
            await _try(prod_svc.craft(db, world, player, "garments", gruns))
        garments = await _inv(db, world, player.id, "garments")
        if garments:
            accord_price = 180  # the ring pins garments well above cost
            if bot.defector and day % 7 >= 5:  # late-tournament betrayal
                price = 150
            elif bot.in_cartel:
                price = accord_price
            else:
                price = await _ask_price(db, world, "garments", rng)
            await _try(market_svc.place_order(db, world, player, "garments", "sell",
                                              garments, max(2, price), ttl_days=2))

    # Shopkeeping: producers stock the posted-price shelf (week 2+) so the
    # retail channel — and the shop UI — has life.
    if bot.persona == "producer" and week >= 2 and rng.random() < 0.5:
        for good in ("bread", "garments", "cloth"):
            held = await _inv(db, world, player.id, good)
            if held >= 3:
                ref = await _close_or(db, world, good, T.GOODS[good].anchor)
                await _try(shops_svc.set_listing(db, world, player, good,
                                                 max(3, round(ref * 1.25)), 2))
                break

    # The coin sink at work: comfortable merchants buy boutique swagger.
    if week >= 3 and player.coins > 500 and rng.random() < 0.08:
        for cid, price in (("peacock", 900), ("fountain_small", 400),
                           ("sign_gilt", 150), ("awning_striped", 80)):
            if player.coins > price + 300:
                await _try(fun_svc.buy_cosmetic(db, world, player, cid))
                break

    # everyone occasionally hits the puzzle for streaks
    if rng.random() < 0.6:
        state = await fun_svc.get_puzzle_state(db, world, player)
        if not state["finished"]:
            lo, hi = 10, 99
            for _ in range(6):
                g = (lo + hi) // 2
                out = await fun_svc.guess_puzzle(db, world, player, g)
                if out["solved"] or out["finished"]:
                    break
                direction, heat = out["feedback"].split(":")
                if direction == "higher":
                    lo = g + 1
                    if heat == "scalding":
                        hi = min(hi, g + 3)
                    elif heat == "warm":
                        lo, hi = max(lo, g + 4), min(hi, g + 10)
                    else:
                        lo = max(lo, g + 11)
                else:
                    hi = g - 1
                    if heat == "scalding":
                        lo = max(lo, g - 3)
                    elif heat == "warm":
                        lo, hi = max(lo, g - 10), min(hi, g - 4)
                    else:
                        hi = min(hi, g - 11)


async def _count_license_holders(db: AsyncSession, world: World) -> int:
    from app.models import License

    rows = (await db.scalars(select(License).where(
        License.world_id == world.id, License.good_id == "glowdye",
        ~License.revoked))).all()
    return len({r.player_id for r in rows})


async def form_cartel(db: AsyncSession, world: World, bots: list[Bot]) -> None:
    cartelists = [b for b in bots if b.persona == "cartelist"]
    if len(cartelists) < 2:
        return
    founder = await db.get(Player, cartelists[0].player_id)
    compact = await compacts_svc.create_compact(
        db, world, founder, "The Garment Ring", "price_accord",
        {"good": "garments", "price": 180})
    cartelists[0].in_cartel = True
    for b in cartelists[1:]:
        member = await db.get(Player, b.player_id)
        await compacts_svc.join_compact(db, world, member, compact.id)
        b.in_cartel = True
    cartelists[-1].defector = True  # someone always cracks

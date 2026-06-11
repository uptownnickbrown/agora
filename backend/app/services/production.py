"""Effort economy: gathering, hand-crafting, facilities, hiring, scrubbers.

Facilities embody fixed vs variable cost (Week 4): build cost is the fixed
cost, inputs+upkeep+wages the variable; worker output has diminishing marginal
returns baked into the curve (spec §6 wk4).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import Facility, Player, World
from .common import GameError, adjust_coins, adjust_goods, emit, get_inventory, spend_effort


async def gather(db: AsyncSession, world: World, player: Player, good_id: str, effort: int) -> int:
    good = T.GOODS.get(good_id)
    if good is None or not good.gatherable:
        raise GameError(f"{good_id} cannot be gathered")
    if good.unlock_week > world.current_week:
        raise GameError(f"{good_id} is not yet available")
    if effort <= 0:
        raise GameError("effort must be positive")
    spend_effort(player, effort)
    mult = T.BALANCE["aptitude_multiplier"] if player.aptitude_good == good_id else 1
    qty = effort * T.BALANCE["gather_yield_per_effort"] * mult
    await adjust_goods(db, world.id, player, good_id, qty)
    player.last_active_day = world.world_day
    await emit(db, world, "gathered", {"good": good_id, "qty": qty, "effort": effort},
               actor=player.id)
    return qty


async def craft(db: AsyncSession, world: World, player: Player, output: str, runs: int = 1) -> int:
    recipe = T.RECIPES.get(output)
    if recipe is None:
        raise GameError(f"no recipe for {output}")
    if recipe.unlock_week > world.current_week:
        raise GameError(f"{output} crafting unlocks in week {recipe.unlock_week}")
    if T.GOODS[output].license_required:
        from .licenses import player_has_license

        if not await player_has_license(db, world, player.id, output):
            raise GameError(f"crafting {output} requires a Crown license")
    if runs <= 0 or runs > 100:
        raise GameError("runs out of range")
    spend_effort(player, recipe.effort * runs)
    for good_id, need in recipe.inputs.items():
        await adjust_goods(db, world.id, player, good_id, -need * runs)
    out_qty = recipe.out_qty * runs
    await adjust_goods(db, world.id, player, output, out_qty)
    player.last_active_day = world.world_day
    await emit(db, world, "crafted", {"good": output, "qty": out_qty}, actor=player.id)
    return out_qty


async def build_facility(db: AsyncSession, world: World, player: Player, kind: str) -> Facility:
    fdef = T.FACILITIES.get(kind)
    if fdef is None:
        raise GameError(f"unknown facility {kind}")
    if fdef.unlock_week > world.current_week:
        raise GameError(f"{fdef.name} unlocks in week {fdef.unlock_week}")
    if T.GOODS[fdef.output].license_required:
        from .licenses import player_has_license

        if not await player_has_license(db, world, player.id, fdef.output):
            raise GameError(f"building a {fdef.name} requires a Crown license")
    cost = fdef.build_cost[0]
    adjust_coins(player, -cost)
    fac = Facility(world_id=world.id, player_id=player.id, kind=kind, tier=1)
    db.add(fac)
    await db.flush()
    await emit(db, world, "facility_built", {"kind": kind, "cost": cost}, actor=player.id)
    return fac


async def upgrade_facility(db: AsyncSession, world: World, player: Player, facility_id) -> Facility:
    fac = await db.get(Facility, facility_id)
    if fac is None or fac.player_id != player.id or fac.world_id != world.id:
        raise GameError("facility not found")
    fdef = T.FACILITIES[fac.kind]
    if fac.tier >= fdef.max_tier:
        raise GameError("already at max tier")
    if fac.tier + 1 >= 2 and world.current_week < 4:
        raise GameError("higher tiers unlock in week 4")
    cost = fdef.build_cost[fac.tier]  # next tier's cost
    adjust_coins(player, -cost)
    fac.tier += 1
    await emit(db, world, "facility_upgraded", {"kind": fac.kind, "tier": fac.tier,
                                                "cost": cost}, actor=player.id)
    return fac


async def hire_workers(db: AsyncSession, world: World, player: Player, facility_id, workers: int) -> Facility:
    if world.current_week < 4:
        raise GameError("hiring unlocks in week 4")
    fac = await db.get(Facility, facility_id)
    if fac is None or fac.player_id != player.id or fac.world_id != world.id:
        raise GameError("facility not found")
    if workers < 0 or workers > 12:
        raise GameError("0-12 workers")
    fac.workers = workers
    await emit(db, world, "workers_set", {"kind": fac.kind, "workers": workers}, actor=player.id)
    return fac


async def buy_scrubber(db: AsyncSession, world: World, player: Player, facility_id) -> Facility:
    if world.current_week < 6:
        raise GameError("scrubbers arrive in week 6")
    fac = await db.get(Facility, facility_id)
    if fac is None or fac.player_id != player.id or fac.world_id != world.id:
        raise GameError("facility not found")
    if fac.scrubber:
        raise GameError("already fitted")
    adjust_coins(player, -T.BALANCE["scrubber_cost"])
    fac.scrubber = True
    await emit(db, world, "scrubber_fitted", {"kind": fac.kind}, actor=player.id)
    return fac


def facility_output(fac: Facility, fdef: T.FacilityDef, smog: int) -> int:
    """Daily output: tier base + diminishing worker bonus, degraded by smog."""
    base = fdef.output_per_day[fac.tier - 1]
    if fac.workers > 0:
        base += round(base * 0.5 * (fac.workers ** T.BALANCE["worker_output_exponent"]) / 2)
    threshold = T.BALANCE["smog_efficiency_threshold"]
    if smog > threshold:
        over = min(1.0, (smog - threshold) / threshold)
        eff = 1.0 - over * (1.0 - T.BALANCE["smog_efficiency_floor"])
        base = round(base * eff)
    return base


async def run_daily_production(db: AsyncSession, world: World) -> dict:
    """Daily close: every active facility produces; upkeep + wages charged;
    smog emitted. Facilities idle (and skip upkeep) when inputs are missing —
    shut-down vs exit intuition (spec §6 wk4)."""
    facilities = (
        await db.scalars(
            select(Facility).where(Facility.world_id == world.id, Facility.active)
        )
    ).all()
    total_emissions = 0
    produced: dict[str, int] = {}
    for fac in facilities:
        fdef = T.FACILITIES[fac.kind]
        player = await db.get(Player, fac.player_id)
        out_qty = facility_output(fac, fdef, world.smog)
        recipe = T.RECIPES.get(fdef.output)
        if recipe is not None:
            inv_ok = True
            for good_id, need in recipe.inputs.items():
                inv = await get_inventory(db, world.id, player.id, good_id)
                if inv.qty < need * out_qty:
                    inv_ok = False
            if not inv_ok:
                # produce what inputs allow
                max_runs = out_qty
                for good_id, need in recipe.inputs.items():
                    inv = await get_inventory(db, world.id, player.id, good_id)
                    max_runs = min(max_runs, inv.qty // need)
                out_qty = max(0, max_runs)
            for good_id, need in recipe.inputs.items():
                if out_qty:
                    await adjust_goods(db, world.id, player, good_id, -need * out_qty)
        if out_qty <= 0:
            continue  # idle: no upkeep, no wages, no output (shut down for the day)
        upkeep = fdef.upkeep[fac.tier - 1]
        wages = fac.workers * T.BALANCE["worker_wage_per_day"]
        cost = upkeep + wages
        if player.coins < cost and not player.is_npc:
            continue  # can't cover variable costs: facility idles
        adjust_coins(player, -cost)
        await adjust_goods(db, world.id, player, fdef.output, out_qty)
        produced[fdef.output] = produced.get(fdef.output, 0) + out_qty
        emissions = fdef.smog_per_unit * out_qty
        if fac.scrubber:
            emissions = round(emissions * T.BALANCE["scrubber_emission_mult"])
        total_emissions += emissions
        smog_tax = (world.market_rules or {}).get("smog_tax_per_unit", 0)
        if smog_tax and emissions:
            adjust_coins(player, -min(player.coins, smog_tax * emissions))
        await emit(db, world, "production",
                   {"kind": fac.kind, "qty": out_qty, "upkeep": upkeep, "wages": wages,
                    "emissions": emissions}, actor=player.id)
    if world.current_week >= 6:
        world.smog = max(0, world.smog + total_emissions - T.BALANCE["smog_decay_per_day"])
    return {"produced": produced, "emissions": total_emissions}


async def regen_effort(db: AsyncSession, world: World) -> None:
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    for p in players:
        p.effort = min(T.BALANCE["effort_cap"], p.effort + T.BALANCE["effort_per_day"])

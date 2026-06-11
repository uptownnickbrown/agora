"""The instructor's intervention catalog (spec §10.3): one-click, diegetic,
parameterized. Every intervention mutates the simulation AND publishes Crier
fiction. Students see the world act; the instructor's hand stays hidden.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CrierPost, Intervention, Player, ScheduledEvent, World
from .common import GameError, adjust_coins, adjust_goods, emit, get_inventory
from .licenses import grant_license, open_auction, revoke_licenses
from .market import last_close
from .npc import shift_schedule

CATALOG = {
    "supply_shock": {"params": ["good", "price_mult", "qty_mult", "days"],
                     "blurb": "Drought, blight, or bumper harvest on one good."},
    "demand_shock": {"params": ["goods", "price_mult", "qty_mult", "days"],
                     "blurb": "Festival, foreign buyer, or fashion craze."},
    "price_ceiling": {"params": ["good", "price"], "blurb": "Legal maximum price."},
    "repeal_ceiling": {"params": ["good"], "blurb": "Repeal a ceiling."},
    "price_floor": {"params": ["good", "price"], "blurb": "Legal minimum price."},
    "repeal_floor": {"params": ["good"], "blurb": "Repeal a floor."},
    "tax": {"params": ["good", "per_unit"], "blurb": "Per-unit tax on sellers."},
    "subsidy": {"params": ["good", "per_unit"], "blurb": "Per-unit production subsidy."},
    "smog_tax": {"params": ["per_unit"], "blurb": "Pigouvian levy per unit of emissions."},
    "fishing_quota": {"params": ["per_player_per_day"], "blurb": "Daily catch quota."},
    "fishery_season": {"params": ["closed"], "blurb": "Open/close the fishery."},
    "license_auction": {"params": ["good", "auction_id", "licenses", "close_day_offset"],
                        "blurb": "Sealed-bid auction of exclusive licenses."},
    "license_grant": {"params": ["good", "player_id"], "blurb": "Grant a license directly."},
    "license_revoke": {"params": ["good", "player_id?"], "blurb": "Revoke license(s)."},
    "antitrust": {"params": ["player_id", "good", "divest_fraction", "fine"],
                  "blurb": "Forced divestiture of hoarded stock plus a fine."},
    "stimulus": {"params": ["amount"], "blurb": "Grant coins to every merchant."},
}


async def preview(kind: str, params: dict) -> str:
    if kind == "supply_shock":
        direction = "tighten sharply" if params.get("qty_mult", 1) < 1 else "swell"
        return (f"NPC supply of {params.get('good')} will {direction} for "
                f"{params.get('days', 3)} days; expect prices to "
                f"{'rise' if params.get('qty_mult', 1) < 1 else 'fall'} over 1-2 days.")
    if kind == "demand_shock":
        return (f"NPC demand for {params.get('goods')} shifts by "
                f"~{params.get('price_mult', 1):.0%} willingness-to-pay for "
                f"{params.get('days', 3)} days.")
    if kind == "price_ceiling":
        return ("If the ceiling binds below market, legal trade will thin or stop, "
                "shortage will appear as unfilled demand, and sellers will withdraw. "
                "Your students will be annoyed. This is the point.")
    return CATALOG.get(kind, {}).get("blurb", "")


async def execute(db: AsyncSession, world: World, kind: str, params: dict,
                  headline: str | None = None) -> dict:
    if kind not in CATALOG:
        raise GameError(f"unknown intervention {kind}")
    handler = _HANDLERS[kind]
    crier_copy = await handler(db, world, params)
    if headline:
        crier_copy = headline
    db.add(Intervention(world_id=world.id, kind=kind, params=params,
                        world_day=world.world_day, crier_copy=crier_copy))
    if crier_copy:
        # First sentence is the headline; the rest is body — never echo both.
        for sep in ("! ", ". "):
            if sep in crier_copy:
                head, rest = crier_copy.split(sep, 1)
                title, body = head + sep.strip(), rest.strip()
                break
        else:
            title, body = crier_copy, ""
        db.add(CrierPost(world_id=world.id, world_day=world.world_day, kind="news",
                         title=title[:200], body=body))
    await emit(db, world, "intervention", {"kind": kind, **{k: v for k, v in params.items()
                                                            if k != "player_id"}})
    return {"kind": kind, "crier": crier_copy}


async def schedule(db: AsyncSession, world: World, kind: str, params: dict, world_day: int) -> None:
    if kind not in CATALOG:
        raise GameError(f"unknown intervention {kind}")
    if world_day <= world.world_day:
        raise GameError("schedule for a future world-day")
    db.add(ScheduledEvent(world_id=world.id, world_day=world_day, kind=kind, params=params))


# -- handlers -------------------------------------------------------------------

async def _supply_shock(db, world, p):
    await shift_schedule(db, world, p["good"], "sell",
                         price_mult=p.get("price_mult", 1.5),
                         qty_mult=p.get("qty_mult", 0.5),
                         revert_after_days=p.get("days", 3))
    worse = p.get("qty_mult", 0.5) < 1
    return (f"{'Disaster in the countryside! ' if worse else 'A bountiful season! '}"
            f"The flow of {p['good']} into the Agora "
            f"{'withers' if worse else 'swells'}.")


async def _demand_shock(db, world, p):
    goods = p.get("goods") or [p.get("good")]
    for g in goods:
        await shift_schedule(db, world, g, "buy",
                             price_mult=p.get("price_mult", 1.5),
                             qty_mult=p.get("qty_mult", 1.5),
                             revert_after_days=p.get("days", 3))
    hot = p.get("price_mult", 1.5) >= 1
    return (f"The town clamors for {', '.join(goods)}!" if hot
            else f"Demand for {', '.join(goods)} falls quiet.")


async def _price_ceiling(db, world, p):
    price = p.get("price")
    if price is None and p.get("anchor") == "pre_shock":
        price = await last_close(db, world, p["good"]) or 50
    rules = dict(world.market_rules or {})
    ceilings = dict(rules.get("ceilings") or {})
    ceilings[p["good"]] = int(price)
    rules["ceilings"] = ceilings
    world.market_rules = rules
    return (f"By royal decree: {p['good']} shall not sell above {price} coppers! "
            f"The Crown congratulates itself on its compassion.")


async def _repeal_ceiling(db, world, p):
    rules = dict(world.market_rules or {})
    ceilings = dict(rules.get("ceilings") or {})
    ceilings.pop(p["good"], None)
    rules["ceilings"] = ceilings
    world.market_rules = rules
    return f"The price decree on {p['good']} is repealed. Merchants exhale."


async def _price_floor(db, world, p):
    rules = dict(world.market_rules or {})
    floors = dict(rules.get("floors") or {})
    floors[p["good"]] = int(p["price"])
    rules["floors"] = floors
    world.market_rules = rules
    return f"The Crown guarantees {p['good']} shall fetch no less than {p['price']} coppers."


async def _repeal_floor(db, world, p):
    rules = dict(world.market_rules or {})
    floors = dict(rules.get("floors") or {})
    floors.pop(p["good"], None)
    rules["floors"] = floors
    world.market_rules = rules
    return f"The price guarantee on {p['good']} is withdrawn."


async def _tax(db, world, p):
    rules = dict(world.market_rules or {})
    taxes = dict(rules.get("taxes") or {})
    taxes[p["good"]] = int(p["per_unit"])
    rules["taxes"] = taxes
    world.market_rules = rules
    return f"A levy of {p['per_unit']} coppers per {p['good']} sold. The Crown thanks you."


async def _subsidy(db, world, p):
    rules = dict(world.market_rules or {})
    subsidies = dict(rules.get("subsidies") or {})
    subsidies[p["good"]] = int(p["per_unit"])
    rules["subsidies"] = subsidies
    world.market_rules = rules
    return f"The Crown will pay {p['per_unit']} coppers atop every {p['good']} sold!"


async def _smog_tax(db, world, p):
    rules = dict(world.market_rules or {})
    rules["smog_tax_per_unit"] = int(p["per_unit"])
    world.market_rules = rules
    return (f"A soot levy! {p['per_unit']} coppers per measure of smoke. "
            f"Scrubber merchants rejoice.")


async def _fishing_quota(db, world, p):
    rules = dict(world.fishing_rules or {})
    rules["quota"] = int(p["per_player_per_day"])
    world.fishing_rules = rules
    return f"Royal fishery quota: {p['per_player_per_day']} fish per merchant per day."


async def _fishery_season(db, world, p):
    rules = dict(world.fishing_rules or {})
    rules["closed"] = bool(p.get("closed"))
    world.fishing_rules = rules
    return ("The fishery is CLOSED until the stocks recover."
            if p.get("closed") else "The fishery reopens!")


async def _license_auction(db, world, p):
    await open_auction(db, world, p["good"], p["auction_id"], p["licenses"],
                       p.get("close_day_offset", 2))
    return (f"The Crown auctions {p['licenses']} exclusive {p['good']} licenses! "
            f"Sealed bids at the Guild Hall.")


async def _license_grant(db, world, p):
    await grant_license(db, world, p["player_id"], p["good"])
    return f"The Crown grants a royal {p['good']} license."


async def _license_revoke(db, world, p):
    n = await revoke_licenses(db, world, p["good"], p.get("player_id"))
    return f"{n} {p['good']} license(s) revoked by royal displeasure."


async def _antitrust(db, world, p):
    player = await db.get(Player, p["player_id"])
    if player is None or player.world_id != world.id:
        raise GameError("player not found")
    inv = await get_inventory(db, world.id, player.id, p["good"])
    divest = round(inv.qty * float(p.get("divest_fraction", 0.5)))
    price = await last_close(db, world, p["good"]) or 10
    if divest > 0:
        await adjust_goods(db, world.id, player, p["good"], -divest)
        adjust_coins(player, divest * max(1, round(price * 0.8)))  # forced sale, below market
    fine = int(p.get("fine", 0))
    if fine:
        adjust_coins(player, -min(player.coins, fine))
    await emit(db, world, "antitrust", {"good": p["good"], "divested": divest, "fine": fine},
               actor=player.id)
    return (f"ANTITRUST! The Crown breaks up a {p['good']} concentration: "
            f"{divest} units divested at a regrettable price, plus a {fine}-copper fine.")


async def _stimulus(db, world, p):
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    for pl in players:
        adjust_coins(pl, int(p["amount"]))
    return f"The Crown showers {p['amount']} coppers upon every merchant. What could go wrong?"


_HANDLERS = {
    "supply_shock": _supply_shock,
    "demand_shock": _demand_shock,
    "price_ceiling": _price_ceiling,
    "repeal_ceiling": _repeal_ceiling,
    "price_floor": _price_floor,
    "repeal_floor": _repeal_floor,
    "tax": _tax,
    "subsidy": _subsidy,
    "smog_tax": _smog_tax,
    "fishing_quota": _fishing_quota,
    "fishery_season": _fishery_season,
    "license_auction": _license_auction,
    "license_grant": _license_grant,
    "license_revoke": _license_revoke,
    "antitrust": _antitrust,
    "stimulus": _stimulus,
}

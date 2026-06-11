"""The "Agora Standard 7-Week" world template (spec §11).

All definition data lives here in code, versioned with the app. Worlds reference
these by string id. One canonical template in v1 — resist configuration sprawl.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TEMPLATE_VERSION = "agora-standard-7wk/1"

DAYS_PER_WEEK = 7


@dataclass(frozen=True)
class Good:
    id: str
    name: str
    tier: str          # raw | processed | finished
    unlock_week: int
    anchor: int        # balance anchor price (coppers) for NPC schedules
    gatherable: bool = False
    license_required: bool = False


GOODS: dict[str, Good] = {
    g.id: g
    for g in [
        Good("grain", "Grain", "raw", 1, 30, gatherable=True),
        Good("wood", "Wood", "raw", 1, 25, gatherable=True),
        Good("wool", "Wool", "raw", 1, 30, gatherable=True),
        Good("fish", "Fish", "raw", 1, 35),  # from the Docks, not gathering
        Good("ore", "Ore", "raw", 4, 45, gatherable=True),
        Good("herbs", "Herbs", "raw", 3, 40, gatherable=True),
        Good("flour", "Flour", "processed", 2, 70),
        Good("lumber", "Lumber", "processed", 2, 60),
        Good("cloth", "Cloth", "processed", 2, 70),
        Good("medicine", "Medicine", "processed", 3, 150),
        Good("iron", "Iron", "processed", 4, 100),
        Good("bread", "Bread", "finished", 2, 150),
        Good("garments", "Garments", "finished", 2, 160),
        Good("tapestries", "Tapestries", "finished", 3, 260),
        Good("tools", "Tools", "finished", 4, 230),
        Good("glowdye", "Glowdye", "finished", 5, 400, license_required=True),
    ]
}


@dataclass(frozen=True)
class Recipe:
    output: str
    inputs: dict[str, int]
    effort: int          # hand-craft effort cost per run
    out_qty: int = 1
    unlock_week: int = 2


RECIPES: dict[str, Recipe] = {
    r.output: r
    for r in [
        Recipe("flour", {"grain": 2}, effort=2),
        Recipe("lumber", {"wood": 2}, effort=2),
        Recipe("cloth", {"wool": 2}, effort=2),
        Recipe("bread", {"flour": 2}, effort=2),
        Recipe("garments", {"cloth": 2}, effort=2),
        Recipe("medicine", {"herbs": 2}, effort=3, unlock_week=3),
        Recipe("tapestries", {"cloth": 3}, effort=4, unlock_week=3),
        Recipe("iron", {"ore": 2}, effort=3, unlock_week=4),
        Recipe("tools", {"iron": 1, "lumber": 1}, effort=3, unlock_week=4),
        Recipe("glowdye", {"herbs": 2, "ore": 1}, effort=4, unlock_week=5),
    ]
}


@dataclass(frozen=True)
class FacilityDef:
    id: str
    name: str
    output: str
    unlock_week: int
    # per tier (index 0 = tier 1): build/upgrade cost, daily output, daily upkeep
    build_cost: tuple[int, ...] = (120, 360, 900)
    output_per_day: tuple[int, ...] = (4, 10, 18)
    upkeep: tuple[int, ...] = (4, 14, 32)
    max_tier: int = 3
    smog_per_unit: int = 1  # emissions per output unit (Week 6)


FACILITIES: dict[str, FacilityDef] = {
    f.id: f
    for f in [
        FacilityDef("farm", "Farm Plot", "grain", 2, smog_per_unit=0),
        FacilityDef("pasture", "Pasture", "wool", 2, smog_per_unit=0),
        FacilityDef("woodlot", "Woodlot", "wood", 2, smog_per_unit=0),
        FacilityDef("herb_garden", "Herb Garden", "herbs", 3, smog_per_unit=0),
        FacilityDef("mine", "Mine", "ore", 4, smog_per_unit=2),
        FacilityDef("mill", "Mill", "flour", 2),
        FacilityDef("loom", "Loom", "cloth", 2),
        FacilityDef("smelter", "Smelter", "iron", 4, smog_per_unit=3),
        FacilityDef("bakery", "Bakery", "bread", 2),
        FacilityDef("tailor", "Tailor Shop", "garments", 2),
        FacilityDef("apothecary", "Apothecary", "medicine", 3),
        FacilityDef("atelier", "Atelier", "tapestries", 3),
        FacilityDef("smithy", "Smithy", "tools", 4, smog_per_unit=2),
        FacilityDef("dyeworks", "Dyeworks", "glowdye", 5, smog_per_unit=2),
    ]
}

# Facility production consumes recipe inputs for its output good (if a recipe
# exists); raw-good facilities consume nothing.

BALANCE = {
    "starting_coins": 200,
    "effort_per_day": 20,
    "effort_cap": 40,
    "gather_yield_per_effort": 1,
    "aptitude_multiplier": 3,
    "order_max_ttl_days": 2,
    "worker_wage_per_day": 12,
    "worker_output_exponent": 0.6,  # diminishing marginal returns (Week 4)
    "scrubber_cost": 250,
    "scrubber_emission_mult": 0.25,
    "smog_decay_per_day": 30,
    "smog_efficiency_threshold": 200,   # above this, facility output degrades
    "smog_efficiency_floor": 0.5,
    "fish_stock_start": 1000,
    "fish_regen_rate_bp": 800,          # 8%/day logistic regen
    "fish_capacity": 1500,
    "fishing_effort_cost": 3,
    "fresh_start_coins": 120,
    "fresh_start_rate_bp": 20,
    "starting_endowment_qty": 30,       # of the aptitude good (deliberately lopsided)
    "merchant_reward_cap": 150,
}

# NPC liquidity: per student of roster size, per good — flows scale with class.
NPC_FLOWS = {
    # good: (supply_qty_factor, demand_qty_factor) per student per day
    "grain": (1.2, 0.3), "wood": (1.0, 0.3), "wool": (1.2, 0.3),
    "ore": (0.8, 0.2), "herbs": (0.8, 0.2), "fish": (0.0, 0.8),
    "flour": (0.2, 0.4), "lumber": (0.2, 0.4), "cloth": (0.2, 0.4),
    "iron": (0.2, 0.3), "medicine": (0.0, 0.6),
    "bread": (0.0, 1.0), "garments": (0.0, 1.0), "tapestries": (0.0, 0.4),
    "tools": (0.0, 0.5), "glowdye": (0.0, 0.5),
}

# Demand bands relative to anchor; medicine is deliberately inelastic (tall band),
# tapestries/glowdye elastic luxuries (narrow band collapses if prices rise).
NPC_BANDS = {
    "default_supply": (0.6, 1.1),
    "default_demand": (0.8, 1.5),
    "demand_overrides": {
        "medicine": (0.9, 3.0),     # the town's sick will pay almost anything
        "tapestries": (0.7, 1.15),  # luxury: demand dies above the anchor
        "glowdye": (0.8, 1.6),
        "bread": (0.8, 1.8),
    },
}

# The seven-week arc: scripted beats created at world launch (spec §6).
# day = world_day (1-indexed); week W spans days (W-1)*7+1 .. W*7.
def standard_script(n_students: int) -> list[dict]:
    def day(week: int, d: int) -> int:
        return (week - 1) * DAYS_PER_WEEK + d

    return [
        # Week 2 — Festival Rush
        {"world_day": day(2, 2), "kind": "announce",
         "params": {"title": "The Lantern Festival approaches!",
                    "body": "In four days the town floods with revelers. Garments and bread will be in furious demand — then the lanterns go out."}},
        {"world_day": day(2, 5), "kind": "demand_shock",
         "params": {"goods": ["garments", "bread"], "price_mult": 1.7, "qty_mult": 1.8,
                    "days": 3, "headline": "The Lantern Festival begins!"}},
        # Week 3 — Drought + Bread Decree
        {"world_day": day(3, 2), "kind": "supply_shock",
         "params": {"good": "grain", "price_mult": 1.6, "qty_mult": 0.45, "days": 10,
                    "headline": "Drought! The fields crack and the grain withers."}},
        {"world_day": day(3, 4), "kind": "price_ceiling",
         "params": {"good": "bread", "anchor": "pre_shock",
                    "headline": "The Royal Granary decrees: bread shall not exceed its old price!"}},
        {"world_day": day(3, 7), "kind": "repeal_ceiling",
         "params": {"good": "bread", "headline": "The Bread Decree is repealed. The Crown is baffled by empty shelves."}},
        # Week 4 — Charter Choice demand swing
        {"world_day": day(4, 2), "kind": "announce",
         "params": {"title": "The Guild offers Charters",
                    "body": "Take a factory charter (great fixed cost, low marginal cost) or stay artisan. Choose your cost structure wisely."}},
        {"world_day": day(4, 3), "kind": "demand_shock",
         "params": {"goods": ["tools", "garments"], "price_mult": 0.7, "qty_mult": 0.6,
                    "days": 2, "headline": "A quiet spell falls over the market."}},
        {"world_day": day(4, 5), "kind": "demand_shock",
         "params": {"goods": ["tools", "garments"], "price_mult": 1.5, "qty_mult": 1.6,
                    "days": 2, "headline": "A trade caravan arrives, hungry for wares!"}},
        # Week 5 — Glowdye licensing
        {"world_day": day(5, 1), "kind": "license_auction_open",
         "params": {"good": "glowdye", "auction_id": "glowdye-1", "licenses": 4,
                    "close_day_offset": 2,
                    "headline": "The Crown auctions 4 exclusive Glowdye licenses! Sealed bids close in two days."}},
        {"world_day": day(5, 5), "kind": "license_auction_open",
         "params": {"good": "glowdye", "auction_id": "glowdye-2", "licenses": 3,
                    "close_day_offset": 2,
                    "headline": "The Second Charter: three more Glowdye licenses go to auction!"}},
        # Week 6 — Gray Skies + commons
        {"world_day": day(6, 1), "kind": "announce",
         "params": {"title": "Gray skies over the district",
                    "body": "The chimneys never stop. Watchers report the famous Agora light is... dimming. Scrubbers are available at the Guild Hall."}},
        {"world_day": day(6, 4), "kind": "smog_tax",
         "params": {"per_unit": 3,
                    "headline": "The Crown imposes a soot levy: 3 coppers per measure of smoke."}},
        {"world_day": day(6, 5), "kind": "fishing_quota",
         "params": {"per_player_per_day": 5,
                    "headline": "Emergency fishery quota: five fish per merchant per day, by royal order."}},
        # Week 7 — tournament
        {"world_day": day(7, 1), "kind": "tournament_start",
         "params": {"headline": "THE MARKET WARS BEGIN — four days, every system, team glory."}},
        {"world_day": day(7, 5), "kind": "tournament_end",
         "params": {"headline": "The Market Wars conclude! The Crier tallies the spoils."}},
    ]

"""Headless scenarios validating the spec's promised economic phenomena.

Each scenario builds a SimWorld populated with NPC schedule traders (the
production liquidity/intervention mechanism) and ~dozens of scripted student
bots, then fast-forwards weeks of play. Tests assert the qualitative arc the
classroom events depend on; the runner prints day-by-day tables for eyeballing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.agents import LinearSchedule, NPCTrader, Producer
from app.engine.orderbook import BUY, SELL
from app.engine.world import SimWorld


@dataclass
class Scenario:
    name: str
    world: SimWorld
    total_days: int
    notes: dict[str, object] = field(default_factory=dict)

    def run(self) -> SimWorld:
        self.world.run_days(self.total_days)
        return self.world


# ---------------------------------------------------------------------------
# 1. Baseline: does the CDA converge to the competitive equilibrium?
# ---------------------------------------------------------------------------

def convergence(seed: int = 7) -> Scenario:
    """Pure NPC double auction. Linear supply (costs 40..80) and demand
    (valuations 60..120) with equal flow cross at p* = 72. Vernon Smith says
    transaction prices should find it; this is the engine's smoke test."""
    world = SimWorld(goods=["grain"], seed=seed)
    world.agents.append(
        NPCTrader("npc_farms", {"grain": LinearSchedule(SELL, 40, 80, qty_per_tick=30)})
    )
    world.agents.append(
        NPCTrader("npc_town", {"grain": LinearSchedule(BUY, 60, 120, qty_per_tick=30)})
    )
    return Scenario("convergence", world, total_days=15, notes={"p_star": 72})


# ---------------------------------------------------------------------------
# 2. Festival Rush (Week 2): announced demand shock -> spike -> lagged supply
#    response -> post-festival glut.
# ---------------------------------------------------------------------------

FESTIVAL_START, FESTIVAL_END = 8, 11  # inclusive World-days


def festival_rush(seed: int = 7, n_students: int = 30) -> Scenario:
    world = SimWorld(goods=["grain", "wool", "bread", "garments"], seed=seed)

    raw_supply = NPCTrader(
        "npc_countryside",
        {
            "grain": LinearSchedule(SELL, 18, 36, qty_per_tick=14),
            "wool": LinearSchedule(SELL, 18, 36, qty_per_tick=14),
        },
    )
    town_demand = NPCTrader(
        "npc_town",
        {
            "bread": LinearSchedule(BUY, 50, 110, qty_per_tick=11),
            "garments": LinearSchedule(BUY, 50, 110, qty_per_tick=11),
        },
    )
    world.agents.extend([raw_supply, town_demand])

    for i in range(n_students):
        start_good = "bread" if i % 2 == 0 else "garments"
        world.agents.append(
            Producer(
                agent_id=f"student_{i:02d}",
                craftable=("bread", "garments"),
                input_good={"bread": "grain", "garments": "wool"},
                unit_costs={"bread": 8, "garments": 8},
                capacity=5,
                retool_days=2,
                current_good=start_good,
            )
        )

    garment_demand = town_demand.schedules["garments"]

    def festival_begins(w: SimWorld) -> None:
        w.announce("lantern_festival")
        garment_demand.price_mult = 1.7
        garment_demand.qty_mult = 1.7

    def festival_ends(w: SimWorld) -> None:
        garment_demand.price_mult = 1.0
        garment_demand.qty_mult = 1.0

    world.schedule(FESTIVAL_START, festival_begins)
    world.schedule(FESTIVAL_END + 1, festival_ends)

    return Scenario(
        "festival_rush",
        world,
        total_days=17,
        notes={"festival": (FESTIVAL_START, FESTIVAL_END), "watch": "garments"},
    )


# ---------------------------------------------------------------------------
# 3. Bread Decree (Week 3): drought supply shock -> price spike -> ceiling at
#    the old price -> shelves empty (sellers exit, demand goes unfilled).
# ---------------------------------------------------------------------------

DROUGHT_DAY, CEILING_DAY = 10, 13


def bread_ceiling(seed: int = 7, n_students: int = 16) -> Scenario:
    world = SimWorld(goods=["grain", "bread"], seed=seed)

    farms = NPCTrader(
        "npc_farms", {"grain": LinearSchedule(SELL, 18, 36, qty_per_tick=14)}
    )
    town = NPCTrader(
        "npc_town", {"bread": LinearSchedule(BUY, 50, 110, qty_per_tick=11)}
    )
    world.agents.extend([farms, town])

    for i in range(n_students):
        world.agents.append(
            Producer(
                agent_id=f"baker_{i:02d}",
                craftable=("bread",),
                input_good={"bread": "grain"},
                unit_costs={"bread": 8},
                capacity=5,
            )
        )

    grain_supply = farms.schedules["grain"]
    notes: dict[str, object] = {"drought_day": DROUGHT_DAY, "ceiling_day": CEILING_DAY}

    def drought(w: SimWorld) -> None:
        w.announce("drought")
        grain_supply.qty_mult = 0.45
        grain_supply.price_mult = 1.6

    def decree(w: SimWorld) -> None:
        # "The old price": the converged pre-drought market, not the spike.
        pre = [s.close for s in w.stats_for("bread")[: DROUGHT_DAY - 1] if s.close]
        ceiling = round(sum(pre[-3:]) / len(pre[-3:]))
        w.announce("bread_decree")
        w.impose_price_ceiling("bread", ceiling)
        notes["ceiling_price"] = ceiling

    world.schedule(DROUGHT_DAY, drought)
    world.schedule(CEILING_DAY, decree)

    return Scenario("bread_ceiling", world, total_days=20, notes=notes)


ALL = {s.__name__: s for s in (convergence, festival_rush, bread_ceiling)}

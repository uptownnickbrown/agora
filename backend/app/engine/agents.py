"""Simulation agents: NPC schedule traders and scripted student bots.

NPC traders are the production mechanism for liquidity and interventions: their
orders derive from piecewise-linear supply/demand schedules, and interventions
mutate those schedules (a drought is a supply-schedule shift, a festival is a
demand-schedule shift). Student bots exist only in the harness — they stand in
for human players so balance and event scripts can be tested in fast-forward.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .orderbook import BUY, SELL

if TYPE_CHECKING:
    from .world import SimWorld


@dataclass
class OrderSpec:
    """An agent's intent; the world assigns ids and enforces market rules."""

    good: str
    side: str
    qty: int
    price: int | None
    ttl_ticks: int = 4


class Agent:
    agent_id: str

    def act(self, world: "SimWorld") -> list[OrderSpec]:
        return []

    def on_day_close(self, world: "SimWorld") -> None:
        pass


@dataclass
class LinearSchedule:
    """A linear demand or supply schedule expressed as unit reservation prices.

    Each tick the trader brings `qty_per_tick` units whose reservation prices are
    spread uniformly across [p_low, p_high] — a discrete linear curve. Demand bids
    at the unit's valuation; supply asks at the unit's cost. Interventions adjust
    `price_mult` (curve shift along the price axis) and `qty_mult` (quantity).
    """

    side: str  # BUY (demand) | SELL (supply)
    p_low: int
    p_high: int
    qty_per_tick: int
    price_mult: float = 1.0
    qty_mult: float = 1.0

    def unit_prices(self, rng: random.Random) -> list[int]:
        n = max(0, round(self.qty_per_tick * self.qty_mult))
        if n == 0:
            return []
        prices = []
        for i in range(n):
            frac = (i + rng.random()) / n  # stratified jitter along the curve
            p = self.p_low + frac * (self.p_high - self.p_low)
            prices.append(max(1, round(p * self.price_mult)))
        return prices


class NPCTrader(Agent):
    """Posts one limit order per schedule unit per tick, short expiry.

    Unfilled demand units that expire are the world's shortage signal.
    """

    def __init__(self, agent_id: str, schedules: dict[str, LinearSchedule]):
        self.agent_id = agent_id
        self.schedules = schedules

    def act(self, world: "SimWorld") -> list[OrderSpec]:
        specs: list[OrderSpec] = []
        for good, sched in self.schedules.items():
            for price in sched.unit_prices(world.rng):
                specs.append(
                    OrderSpec(good=good, side=sched.side, qty=1, price=price, ttl_ticks=3)
                )
        return specs


@dataclass
class Producer(Agent):
    """Harness stand-in for a student: produces one good per day, sells it.

    Captures the two behaviors the event scripts depend on:
    - supply responds to price with a retooling lag (Festival Rush needs the
      spike to precede the supply response, and the glut to follow it);
    - sellers exit when price is forced below cost (the Bread Decree shortage).
    """

    agent_id: str = ""
    craftable: tuple[str, ...] = ()
    input_good: dict[str, str] = field(default_factory=dict)   # output -> raw input
    unit_costs: dict[str, int] = field(default_factory=dict)   # non-input cost/unit
    capacity: int = 6                                          # units per day
    retool_days: int = 2
    margin: float = 1.12

    current_good: str = ""
    retooling: int = 0
    inventory: dict[str, int] = field(default_factory=dict)
    raw_inventory: dict[str, int] = field(default_factory=dict)
    paid_for_raw: dict[str, int] = field(default_factory=dict)  # rolling avg cost
    days_unsold: dict[str, int] = field(default_factory=dict)
    starved_days: int = 0  # consecutive days production ran short of inputs
    _sold_today: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.current_good and self.craftable:
            self.current_good = self.craftable[0]

    # -- helpers --------------------------------------------------------

    def _expected_margin(self, world: "SimWorld", good: str) -> float:
        price = world.demand_signal(good)
        if price is None:
            return 0.0
        cost = self.unit_costs.get(good, 0)
        raw = self.input_good.get(good)
        if raw is not None:
            raw_price = world.last_close(raw) or self.paid_for_raw.get(raw, 0)
            cost += raw_price
        return price - cost

    def unit_cost(self, world: "SimWorld", good: str) -> int:
        cost = self.unit_costs.get(good, 0)
        raw = self.input_good.get(good)
        if raw is not None:
            cost += self.paid_for_raw.get(raw) or world.last_close(raw) or 0
        return cost

    # -- agent interface --------------------------------------------------

    def act(self, world: "SimWorld") -> list[OrderSpec]:
        specs: list[OrderSpec] = []
        rng = world.rng

        # Buy raw input for tomorrow's production run. Input demand is DERIVED
        # demand: never pay more than the output market justifies (a ceiling on
        # the output therefore suppresses input bidding — correct pass-through),
        # but chase scarce inputs harder the longer production has been starved.
        raw = self.input_good.get(self.current_good)
        if raw is not None and self.retooling == 0:
            have = self.raw_inventory.get(raw, 0)
            need = self.capacity - have
            if need > 0:
                out_signal = world.demand_signal(self.current_good)
                ceiling = world.price_ceilings.get(self.current_good)
                if out_signal is not None and ceiling is not None:
                    out_signal = min(out_signal, ceiling)
                willing = (
                    None
                    if out_signal is None
                    else out_signal - self.unit_costs.get(self.current_good, 0) - 1
                )
                ref = world.last_close(raw) or world.best_ask(raw)
                if ref is not None and (willing is None or willing > 0):
                    chase = 1.04 + 0.10 * min(self.starved_days, 3)
                    bid = round(ref * (chase + rng.uniform(0.0, 0.04)))
                    if willing is not None:
                        bid = min(bid, willing)
                    if bid >= 1:
                        specs.append(OrderSpec(good=raw, side=BUY, qty=need, price=bid))

        # Sell finished inventory. Undercut as stock piles up; after a saleless
        # day, hit the standing bid (downward price discovery — without this a
        # stale spike close deadlocks the market: asks anchor high, nothing
        # trades, the close never updates).
        for good, qty in list(self.inventory.items()):
            if qty <= 0:
                continue
            ref = world.demand_signal(good)
            if ref is None:
                continue
            pressure = min(0.25, 0.02 * qty)
            ask = max(1, round(ref * (1.0 - pressure + rng.uniform(-0.03, 0.03))))
            floor = max(1, round(self.unit_cost(world, good) * 1.02))
            if self.days_unsold.get(good, 0) >= 1:
                live_bid = world.best_bid(good)
                if live_bid is not None:
                    ask = min(ask, live_bid)
            ask = max(ask, floor)
            legal_cap = world.price_ceilings.get(good)
            if legal_cap is not None and floor <= legal_cap:
                ask = min(ask, legal_cap)  # still profitable at the ceiling: comply
            # If floor > ceiling the honest ask goes in anyway; the market rules
            # reject it and count the withdrawal — that visible exit IS the shortage.
            sell_qty = min(qty, max(1, qty // 2 + 1))
            specs.append(OrderSpec(good=good, side=SELL, qty=sell_qty, price=ask, ttl_ticks=6))
        return specs

    def on_trade(self, good: str, side: str, qty: int, price: int) -> None:
        if side == BUY:
            self.raw_inventory[good] = self.raw_inventory.get(good, 0) + qty
            prev = self.paid_for_raw.get(good)
            self.paid_for_raw[good] = price if prev is None else round((prev + price) / 2)
        else:
            self.inventory[good] = max(0, self.inventory.get(good, 0) - qty)
            self._sold_today.add(good)

    def on_day_close(self, world: "SimWorld") -> None:
        for good, qty in self.inventory.items():
            if qty > 0 and good not in self._sold_today:
                self.days_unsold[good] = self.days_unsold.get(good, 0) + 1
            else:
                self.days_unsold[good] = 0
        self._sold_today.clear()

        # Produce today's run.
        if self.retooling > 0:
            self.retooling -= 1
        else:
            raw = self.input_good.get(self.current_good)
            run = self.capacity
            if raw is not None:
                run = min(run, self.raw_inventory.get(raw, 0))
                self.raw_inventory[raw] = self.raw_inventory.get(raw, 0) - run
            if run > 0:
                self.inventory[self.current_good] = (
                    self.inventory.get(self.current_good, 0) + run
                )
            self.starved_days = self.starved_days + 1 if run < self.capacity else 0

        # Consider switching to the best-margin good (with retooling cost).
        # Probabilistic + absolute-gap hysteresis: a real class is heterogeneous,
        # so the supply response should be gradual, not a lockstep herd flip
        # (which empties production and thrashes the market).
        if len(self.craftable) > 1 and self.retooling == 0:
            margins = {g: self._expected_margin(world, g) for g in self.craftable}
            best = max(margins, key=margins.get)  # type: ignore[arg-type]
            gap = margins[best] - margins[self.current_good]
            if best != self.current_good and gap > 10 and world.rng.random() < 0.35:
                self.current_good = best
                self.retooling = self.retool_days

"""SimWorld: a deterministic, DB-free instance of the Agora economy.

The production server wraps this same logic with persistence and an API; the
harness drives it in fast-forward. World time is logical: `ticks_per_day` fast
ticks then a daily close, mirroring the production tick model (spec §12.2).
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Callable

from .agents import Agent, OrderSpec, Producer
from .orderbook import BUY, Order, OrderBook, Trade


@dataclass
class DailyStats:
    day: int
    good: str
    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None
    volume: int = 0
    unfilled_demand: int = 0   # NPC/agent bid units that expired unfilled today
    unfilled_supply: int = 0
    suppressed_orders: int = 0  # seller withdrawals forced by a price control
    best_bid_close: int | None = None  # highest unfilled bid at the close
    best_ask_close: int | None = None


@dataclass
class SimWorld:
    goods: list[str]
    seed: int = 7
    ticks_per_day: int = 8

    tick: int = 0
    day: int = 0
    rng: random.Random = field(init=False)
    books: dict[str, OrderBook] = field(init=False)
    agents: list[Agent] = field(default_factory=list)
    price_ceilings: dict[str, int] = field(default_factory=dict)
    price_floors: dict[str, int] = field(default_factory=dict)
    announcements: dict[str, int] = field(default_factory=dict)  # name -> day announced
    history: list[DailyStats] = field(default_factory=list)
    _events: list[tuple[int, Callable[["SimWorld"], None]]] = field(default_factory=list)
    _order_ids: itertools.count = field(default_factory=itertools.count, init=False)
    _day_trades: dict[str, list[Trade]] = field(init=False)
    _day_stats: dict[str, DailyStats] = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.books = {g: OrderBook(g) for g in self.goods}
        self._reset_day_accumulators()

    # -- market data ------------------------------------------------------

    def last_close(self, good: str) -> int | None:
        for stats in reversed(self.history):
            if stats.good == good and stats.close is not None:
                return stats.close
        return None

    def best_bid(self, good: str) -> int | None:
        return self.books[good].best_bid()

    def best_ask(self, good: str) -> int | None:
        return self.books[good].best_ask()

    def closes(self, good: str) -> list[int | None]:
        return [s.close for s in self.history if s.good == good]

    def demand_signal(self, good: str) -> int | None:
        """Best observable price for a would-be seller: yesterday's close OR the
        highest bid left standing at yesterday's close (visible unfilled demand),
        whichever is higher. Without the bid leg, a market that stops trading
        emits no signal and supply never responds to a demand shock."""
        candidates: list[int] = []
        close = self.last_close(good)
        if close is not None:
            candidates.append(close)
        for stats in reversed(self.history):
            if stats.good == good:
                if stats.best_bid_close is not None:
                    candidates.append(stats.best_bid_close)
                break
        live_bid = self.best_bid(good)
        if live_bid is not None:
            candidates.append(live_bid)
        return max(candidates) if candidates else None

    def stats_for(self, good: str) -> list[DailyStats]:
        return [s for s in self.history if s.good == good]

    # -- scheduling ---------------------------------------------------------

    def schedule(self, day: int, effect: Callable[["SimWorld"], None]) -> None:
        self._events.append((day, effect))

    def announce(self, name: str) -> None:
        self.announcements[name] = self.day

    # -- order intake (market rules live here, not in the book) -------------

    def submit_spec(self, agent: Agent, spec: OrderSpec) -> list[Trade]:
        ceiling = self.price_ceilings.get(spec.good)
        floor = self.price_floors.get(spec.good)
        price = spec.price
        if price is not None:
            if ceiling is not None and price > ceiling:
                if spec.side == BUY:
                    price = ceiling  # buyers happily pay the legal maximum
                else:
                    # A seller unwilling to sell at the legal price simply exits.
                    self._day_stats[spec.good].suppressed_orders += 1
                    return []
            if floor is not None and price < floor:
                if spec.side == BUY:
                    self._day_stats[spec.good].suppressed_orders += 1
                    return []
                price = floor  # sellers accept the legal minimum
        order = Order(
            order_id=next(self._order_ids),
            agent_id=agent.agent_id,
            good=spec.good,
            side=spec.side,
            qty=spec.qty,
            price=price,
            placed_tick=self.tick,
            expires_tick=self.tick + spec.ttl_ticks,
        )
        trades = self.books[spec.good].submit(order, self.tick)
        if trades:
            self._record_trades(spec.good, trades)
        return trades

    def _record_trades(self, good: str, trades: list[Trade]) -> None:
        self._day_trades[good].extend(trades)
        by_agent = {a.agent_id: a for a in self.agents}
        for t in trades:
            stats = self._day_stats[good]
            stats.volume += t.qty
            stats.open = t.price if stats.open is None else stats.open
            stats.high = t.price if stats.high is None else max(stats.high, t.price)
            stats.low = t.price if stats.low is None else min(stats.low, t.price)
            stats.close = t.price
            for agent_id, side in ((t.buyer_id, BUY), (t.seller_id, "sell")):
                agent = by_agent.get(agent_id)
                if isinstance(agent, Producer):
                    agent.on_trade(good, side, t.qty, t.price)

    # -- time ---------------------------------------------------------------

    def step(self) -> None:
        self.tick += 1
        for good, book in self.books.items():
            for dead, unfilled in book.expire(self.tick):
                stats = self._day_stats[good]
                if dead.side == BUY:
                    stats.unfilled_demand += unfilled
                else:
                    stats.unfilled_supply += unfilled
        order = list(self.agents)
        self.rng.shuffle(order)
        for agent in order:
            for spec in agent.act(self):
                self.submit_spec(agent, spec)

    def run_day(self) -> None:
        self.day += 1
        for day, effect in [e for e in self._events if e[0] == self.day]:
            effect(self)
        self._events = [e for e in self._events if e[0] != self.day]
        for _ in range(self.ticks_per_day):
            self.step()
        self._close_day()

    def run_days(self, n: int) -> None:
        for _ in range(n):
            self.run_day()

    def _close_day(self) -> None:
        # Expire everything resting at close (daily close clears stale orders).
        for good, book in self.books.items():
            stats = self._day_stats[good]
            stats.best_bid_close = book.best_bid()
            stats.best_ask_close = book.best_ask()
            for o in list(book.open_orders.values()):
                if o.side == BUY:
                    stats.unfilled_demand += o.remaining
                else:
                    stats.unfilled_supply += o.remaining
                book.cancel(o.order_id)
        self.history.extend(self._day_stats.values())
        self._reset_day_accumulators()
        for agent in self.agents:
            agent.on_day_close(self)

    def _reset_day_accumulators(self) -> None:
        self._day_trades = {g: [] for g in self.goods}
        self._day_stats = {g: DailyStats(day=self.day + 1, good=g) for g in self.goods}

    # -- interventions (diegetic wrappers live in the pedagogy layer) -------

    def impose_price_ceiling(self, good: str, price: int) -> None:
        self.price_ceilings[good] = price

    def repeal_price_ceiling(self, good: str) -> None:
        self.price_ceilings.pop(good, None)

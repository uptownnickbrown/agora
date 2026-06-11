"""Continuous double auction order book.

Pure logic, no I/O, no DB. Prices are integer coppers, quantities integer units.
Matching is price-time priority with partial fills; trades execute at the resting
order's price. This module is shared verbatim between the production server and
the headless simulation harness.
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field


BUY = "buy"
SELL = "sell"


@dataclass
class Order:
    order_id: int
    agent_id: str
    good: str
    side: str  # BUY | SELL
    qty: int
    price: int | None  # None = market order (never rests on the book)
    placed_tick: int
    expires_tick: int | None = None
    remaining: int = field(default=0)

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("qty must be positive")
        if self.price is not None and self.price <= 0:
            raise ValueError("price must be positive")
        if self.remaining == 0:
            self.remaining = self.qty

    @property
    def is_open(self) -> bool:
        return self.remaining > 0


@dataclass(frozen=True)
class Trade:
    good: str
    price: int
    qty: int
    buyer_id: str
    seller_id: str
    buy_order_id: int
    sell_order_id: int
    tick: int


class OrderBook:
    """One good's book. Bids and asks are lazy heaps keyed by price-time priority."""

    def __init__(self, good: str):
        self.good = good
        self._bids: list[tuple[int, int, Order]] = []  # (-price, seq, order)
        self._asks: list[tuple[int, int, Order]] = []  # (price, seq, order)
        self._seq = itertools.count()
        self.open_orders: dict[int, Order] = {}

    # -- inspection ---------------------------------------------------------

    def _peek(self, heap: list[tuple[int, int, Order]]) -> Order | None:
        while heap:
            _, _, order = heap[0]
            if order.is_open:
                return order
            heapq.heappop(heap)
        return None

    def best_bid(self) -> int | None:
        order = self._peek(self._bids)
        return order.price if order else None

    def best_ask(self) -> int | None:
        order = self._peek(self._asks)
        return order.price if order else None

    def depth(self, side: str) -> int:
        heap = self._bids if side == BUY else self._asks
        return sum(o.remaining for _, _, o in heap if o.is_open)

    # -- mutation -----------------------------------------------------------

    def cancel(self, order_id: int) -> bool:
        order = self.open_orders.pop(order_id, None)
        if order is None or not order.is_open:
            return False
        order.remaining = 0
        return True

    def expire(self, tick: int) -> list[tuple[Order, int]]:
        """Kill resting orders whose expiry has passed.

        Returns (order, unfilled_qty) pairs — the qty must be captured before
        zeroing, since callers use it to measure unmet demand/supply.
        """
        expired = [
            (o, o.remaining) for o in self.open_orders.values()
            if o.expires_tick is not None and o.expires_tick <= tick and o.is_open
        ]
        for o, _ in expired:
            o.remaining = 0
            del self.open_orders[o.order_id]
        return expired

    def submit(self, order: Order, tick: int) -> list[Trade]:
        """Match an incoming order, resting any unfilled limit remainder."""
        if order.good != self.good:
            raise ValueError(f"order good {order.good!r} != book good {self.good!r}")

        contra = self._asks if order.side == BUY else self._bids
        trades: list[Trade] = []
        own_stash: list[tuple[int, int, Order]] = []  # self-trade prevention

        while order.remaining > 0 and contra:
            key_price, seq, resting = contra[0]
            if not resting.is_open:
                heapq.heappop(contra)
                continue
            if resting.agent_id == order.agent_id:
                own_stash.append(heapq.heappop(contra))
                continue
            resting_price = resting.price
            assert resting_price is not None  # market orders never rest
            if order.price is not None:
                if order.side == BUY and resting_price > order.price:
                    break
                if order.side == SELL and resting_price < order.price:
                    break

            fill = min(order.remaining, resting.remaining)
            order.remaining -= fill
            resting.remaining -= fill
            buyer, seller = (
                (order, resting) if order.side == BUY else (resting, order)
            )
            trades.append(
                Trade(
                    good=self.good,
                    price=resting_price,
                    qty=fill,
                    buyer_id=buyer.agent_id,
                    seller_id=seller.agent_id,
                    buy_order_id=buyer.order_id,
                    sell_order_id=seller.order_id,
                    tick=tick,
                )
            )
            if resting.remaining == 0:
                heapq.heappop(contra)
                self.open_orders.pop(resting.order_id, None)

        for item in own_stash:
            heapq.heappush(contra, item)

        if order.remaining > 0 and order.price is not None:
            book = self._bids if order.side == BUY else self._asks
            key = -order.price if order.side == BUY else order.price
            heapq.heappush(book, (key, next(self._seq), order))
            self.open_orders[order.order_id] = order

        return trades

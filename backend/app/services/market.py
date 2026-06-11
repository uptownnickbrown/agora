"""Live order-book markets, persisted. Matching reuses app.engine.orderbook.

Escrow model (humans): buy limits escrow coins at the limit price (difference
refunded on better fills); sells escrow goods. NPCs skip escrow — minting and
absorbing is what liquidity provision means. Price controls, taxes and
subsidies are market rules applied here at intake/fill time (spec §10.3).
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..engine.orderbook import Order as EngineOrder
from ..engine.orderbook import OrderBook
from ..models import DbOrder, DbTrade, Player, PriceSnapshot, World
from .common import GameError, adjust_coins, adjust_goods, emit
from .worlds import good_unlocked


async def _next_seq(db: AsyncSession, world_id: uuid.UUID) -> int:
    cur = await db.scalar(
        select(func.max(DbOrder.seq)).where(DbOrder.world_id == world_id)
    )
    return (cur or 0) + 1


def _rules(world: World) -> dict:
    return world.market_rules or {}


async def place_order(
    db: AsyncSession,
    world: World,
    player: Player,
    good_id: str,
    side: str,
    qty: int,
    price: int | None,
    ttl_days: int = 1,
) -> dict:
    """Returns {order_id|None, trades: [...], status}."""
    if side not in ("buy", "sell"):
        raise GameError("side must be buy or sell")
    if qty <= 0 or qty > 10_000:
        raise GameError("quantity out of range")
    if price is not None and not (0 < price <= 1_000_000):
        raise GameError("price out of range")
    if not good_unlocked(world, good_id):
        raise GameError(f"{good_id} is not yet traded in this world")
    good = T.GOODS[good_id]
    if good.license_required and side == "sell" and not player.is_npc:
        from .licenses import player_has_license

        if not await player_has_license(db, world, player.id, good_id):
            raise GameError(f"selling {good_id} requires a Crown license")
    ttl_days = max(1, min(ttl_days, T.BALANCE["order_max_ttl_days"]))

    rules = _rules(world)
    ceiling = (rules.get("ceilings") or {}).get(good_id)
    floor = (rules.get("floors") or {}).get(good_id)
    market_order = price is None
    if price is not None:
        if ceiling is not None and price > ceiling:
            if side == "buy":
                price = ceiling  # buyers happily pay the legal maximum
            else:
                await emit(db, world, "ask_suppressed",
                           {"good": good_id, "price": price, "qty": qty}, actor=player.id)
                return {"order_id": None, "trades": [], "status": "suppressed"}
        if floor is not None and price < floor:
            if side == "sell":
                price = floor
            else:
                await emit(db, world, "bid_suppressed",
                           {"good": good_id, "price": price, "qty": qty}, actor=player.id)
                return {"order_id": None, "trades": [], "status": "suppressed"}

    # Escrow.
    if not player.is_npc:
        if side == "sell":
            await adjust_goods(db, world.id, player, good_id, -qty)
        elif price is not None:
            adjust_coins(player, -price * qty)
        else:
            # Market buy: bound qty by purchasing power at the best ask later;
            # escrow nothing, validate per-fill below.
            pass

    # Load the live book and match through the shared engine.
    open_rows = (
        await db.scalars(
            select(DbOrder)
            .where(
                DbOrder.world_id == world.id,
                DbOrder.good_id == good_id,
                DbOrder.status == "open",
                DbOrder.side != side,
            )
            .order_by(DbOrder.seq)
        )
    ).all()
    book = OrderBook(good_id)
    row_by_eid: dict[int, DbOrder] = {}
    for i, row in enumerate(open_rows):
        eo = EngineOrder(
            order_id=i, agent_id=str(row.player_id), good=good_id, side=row.side,
            qty=row.remaining, price=row.price, placed_tick=0,
        )
        book.submit(eo, tick=0)
        row_by_eid[i] = row

    seq = await _next_seq(db, world.id)
    incoming_eid = len(open_rows)
    incoming = EngineOrder(
        order_id=incoming_eid, agent_id=str(player.id), good=good_id, side=side,
        qty=qty, price=price, placed_tick=1,
    )
    fills = book.submit(incoming, tick=1)

    # Persist fills.
    trades_out = []
    filled_qty = 0
    players_cache: dict[uuid.UUID, Player] = {player.id: player}

    async def load_player(pid: uuid.UUID) -> Player:
        if pid not in players_cache:
            players_cache[pid] = await db.get(Player, pid)
        return players_cache[pid]

    taxes = (rules.get("taxes") or {})
    subsidies = (rules.get("subsidies") or {})
    tax = taxes.get(good_id, 0)
    subsidy = subsidies.get(good_id, 0)

    for f in fills:
        resting_eid = f.sell_order_id if side == "buy" else f.buy_order_id
        resting = row_by_eid[resting_eid]
        buyer_id = player.id if side == "buy" else resting.player_id
        seller_id = resting.player_id if side == "buy" else player.id
        buyer = await load_player(buyer_id)
        seller = await load_player(seller_id)
        cost = f.price * f.qty

        if side == "buy" and not player.is_npc:
            if price is None:
                if player.coins < cost:
                    break  # market buy ran out of coins; stop filling
                adjust_coins(player, -cost)
            else:
                # escrowed at limit; refund the improvement
                adjust_coins(player, (price - f.price) * f.qty)
        elif side == "buy" and player.is_npc:
            pass  # NPC buyer mints
        if buyer is not player or player.is_npc:
            pass
        # Goods to buyer; proceeds (minus tax, plus subsidy) to seller.
        await adjust_goods(db, world.id, buyer, good_id, f.qty)
        proceeds = cost - tax * f.qty + subsidy * f.qty
        if not seller.is_npc:
            adjust_coins(seller, max(0, proceeds))
        # Resting-buyer escrow: resting buy orders escrowed at their limit ==
        # fill price (engine executes at resting price), so nothing extra moves.
        if side == "sell" and not buyer.is_npc:
            pass  # already escrowed at resting limit == f.price

        resting.remaining -= f.qty
        if resting.remaining == 0:
            resting.status = "filled"
        filled_qty += f.qty
        trade = DbTrade(
            world_id=world.id, good_id=good_id,
            buyer_player_id=buyer_id, seller_player_id=seller_id,
            price=f.price, qty=f.qty, world_day=world.world_day,
        )
        db.add(trade)
        await emit(db, world, "trade",
                   {"good": good_id, "price": f.price, "qty": f.qty,
                    "buyer": str(buyer_id), "seller": str(seller_id)},
                   actor=player.id)
        trades_out.append({"good_id": good_id, "price": f.price, "qty": f.qty})

    remaining = qty - filled_qty
    order_row = None
    if remaining > 0 and not market_order:
        order_row = DbOrder(
            world_id=world.id, player_id=player.id, good_id=good_id, side=side,
            qty=qty, remaining=remaining, price=price, status="open",
            placed_day=world.world_day, expires_day=world.world_day + ttl_days - 1,
            seq=seq,
        )
        db.add(order_row)
        await db.flush()
    elif remaining > 0 and market_order and side == "sell" and not player.is_npc:
        # unfilled market-sell remainder: return escrowed goods
        await adjust_goods(db, world.id, player, good_id, remaining)

    if not player.is_npc:
        player.last_active_day = world.world_day
    await emit(db, world, "order_placed",
               {"good": good_id, "side": side, "qty": qty, "price": price,
                "filled": filled_qty}, actor=player.id)
    return {
        "order_id": str(order_row.id) if order_row else None,
        "trades": trades_out,
        "status": "open" if order_row else ("filled" if filled_qty else "unfilled"),
    }


async def cancel_order(db: AsyncSession, world: World, player: Player, order_id: uuid.UUID) -> None:
    row = await db.get(DbOrder, order_id)
    if row is None or row.world_id != world.id or row.player_id != player.id:
        raise GameError("order not found")
    if row.status != "open":
        raise GameError("order is not open")
    await _release(db, world, row, "cancelled")
    await emit(db, world, "order_cancelled", {"order": str(order_id)}, actor=player.id)


async def _release(db: AsyncSession, world: World, row: DbOrder, status: str) -> None:
    """Refund escrow on an open order and close it."""
    player = await db.get(Player, row.player_id)
    if not player.is_npc:
        if row.side == "buy":
            adjust_coins(player, row.price * row.remaining)
        else:
            await adjust_goods(db, world.id, player, row.good_id, row.remaining)
    row.status = status


async def expire_orders(db: AsyncSession, world: World) -> dict[str, int]:
    """Daily close: expire stale orders; returns unfilled bid units per good."""
    rows = (
        await db.scalars(
            select(DbOrder).where(
                DbOrder.world_id == world.id,
                DbOrder.status == "open",
                DbOrder.expires_day <= world.world_day,
            )
        )
    ).all()
    unfilled_demand: dict[str, int] = {}
    for row in rows:
        if row.side == "buy":
            unfilled_demand[row.good_id] = unfilled_demand.get(row.good_id, 0) + row.remaining
        await _release(db, world, row, "expired")
    return unfilled_demand


async def snapshot_day(db: AsyncSession, world: World, unfilled: dict[str, int]) -> None:
    """Official OHLCV per good for the closing day."""
    trades = (
        await db.scalars(
            select(DbTrade).where(
                DbTrade.world_id == world.id, DbTrade.world_day == world.world_day
            ).order_by(DbTrade.created_at)
        )
    ).all()
    by_good: dict[str, list[DbTrade]] = {}
    for t in trades:
        by_good.setdefault(t.good_id, []).append(t)

    from ..models import EconEvent

    suppressed_rows = (
        await db.execute(
            select(EconEvent.payload).where(
                EconEvent.world_id == world.id,
                EconEvent.world_day == world.world_day,
                EconEvent.kind == "ask_suppressed",
            )
        )
    ).scalars().all()
    suppressed_by_good: dict[str, int] = {}
    for payload in suppressed_rows:
        g = payload.get("good")
        suppressed_by_good[g] = suppressed_by_good.get(g, 0) + payload.get("qty", 1)

    for good_id in T.GOODS:
        if not good_unlocked(world, good_id):
            continue
        ts = by_good.get(good_id, [])
        prices = [t.price for t in ts]
        db.add(PriceSnapshot(
            world_id=world.id, good_id=good_id, world_day=world.world_day,
            open=prices[0] if prices else None,
            high=max(prices) if prices else None,
            low=min(prices) if prices else None,
            close=prices[-1] if prices else None,
            volume=sum(t.qty for t in ts),
            unfilled_demand=unfilled.get(good_id, 0),
            suppressed_asks=suppressed_by_good.get(good_id, 0),
        ))


async def last_close(db: AsyncSession, world: World, good_id: str) -> int | None:
    return await db.scalar(
        select(PriceSnapshot.close)
        .where(
            PriceSnapshot.world_id == world.id,
            PriceSnapshot.good_id == good_id,
            PriceSnapshot.close.is_not(None),
        )
        .order_by(PriceSnapshot.world_day.desc())
        .limit(1)
    )


async def best_bid(db: AsyncSession, world: World, good_id: str) -> int | None:
    return await db.scalar(
        select(func.max(DbOrder.price)).where(
            DbOrder.world_id == world.id, DbOrder.good_id == good_id,
            DbOrder.side == "buy", DbOrder.status == "open")
    )


async def book_snapshot(db: AsyncSession, world: World, good_id: str, depth: int = 8) -> dict:
    rows = (
        await db.scalars(
            select(DbOrder).where(
                DbOrder.world_id == world.id,
                DbOrder.good_id == good_id,
                DbOrder.status == "open",
            )
        )
    ).all()
    bids: dict[int, int] = {}
    asks: dict[int, int] = {}
    for r in rows:
        levels = bids if r.side == "buy" else asks
        levels[r.price] = levels.get(r.price, 0) + r.remaining
    return {
        "good_id": good_id,
        "bids": sorted(bids.items(), key=lambda kv: -kv[0])[:depth],
        "asks": sorted(asks.items(), key=lambda kv: kv[0])[:depth],
    }


async def price_history(db: AsyncSession, world: World, good_id: str) -> list[dict]:
    rows = (
        await db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.world_id == world.id, PriceSnapshot.good_id == good_id)
            .order_by(PriceSnapshot.world_day)
        )
    ).all()
    return [
        {"day": r.world_day, "open": r.open, "high": r.high, "low": r.low,
         "close": r.close, "volume": r.volume, "unfilled_demand": r.unfilled_demand}
        for r in rows
    ]


async def trade_tape(db: AsyncSession, world: World, good_id: str, limit: int = 30) -> list[dict]:
    """Anonymous live tape (DECISIONS.md #11) — names appear only in the Crier."""
    rows = (
        await db.scalars(
            select(DbTrade)
            .where(DbTrade.world_id == world.id, DbTrade.good_id == good_id)
            .order_by(DbTrade.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [{"price": t.price, "qty": t.qty, "day": t.world_day} for t in rows]

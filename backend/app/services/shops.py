"""Player shops: posted-price retail. NPC retail demand samples each listing
against its price at daily close — every student's personal demand-curve lab
(spec §12.3), and later the home of monopolistic competition.
"""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import Player, ShopListing, World
from .common import GameError, adjust_coins, adjust_goods, emit
from .market import last_close
from .worlds import good_unlocked


async def set_listing(
    db: AsyncSession, world: World, player: Player, good_id: str, price: int, stock_qty: int
) -> ShopListing:
    if not good_unlocked(world, good_id):
        raise GameError(f"{good_id} is not yet traded")
    if price <= 0 or price > 1_000_000:
        raise GameError("price out of range")
    if stock_qty < 0:
        raise GameError("stock cannot be negative")
    listing = await db.scalar(
        select(ShopListing).where(
            ShopListing.world_id == world.id,
            ShopListing.player_id == player.id,
            ShopListing.good_id == good_id,
        )
    )
    if listing is None:
        listing = ShopListing(world_id=world.id, player_id=player.id, good_id=good_id,
                              price=price, qty=0)
        db.add(listing)
        await db.flush()
    delta = stock_qty - listing.qty
    if delta > 0:
        await adjust_goods(db, world.id, player, good_id, -delta)  # move into the shop
    elif delta < 0:
        await adjust_goods(db, world.id, player, good_id, -delta)
    listing.qty = stock_qty
    listing.price = price
    player.last_active_day = world.world_day
    await emit(db, world, "shop_listed", {"good": good_id, "price": price, "qty": stock_qty},
               actor=player.id)
    return listing


async def run_retail_demand(db: AsyncSession, world: World, rng: random.Random | None = None) -> int:
    """Daily close: passersby buy from shops. Demand falls with price relative
    to the market close (or anchor): qty ~ base * (ref/price)^2, elastic."""
    seed = (world.config or {}).get("rng_seed", world.id)
    rng = rng or random.Random(f"retail:{seed}:{world.world_day}")
    listings = (
        await db.scalars(
            select(ShopListing).where(ShopListing.world_id == world.id, ShopListing.qty > 0)
        )
    ).all()
    total_sold = 0
    for listing in listings:
        ref = await last_close(db, world, listing.good_id) or T.GOODS[listing.good_id].anchor
        ratio = ref / listing.price
        base = 4.0
        expected = base * min(4.0, ratio ** 2)
        qty = min(listing.qty, int(expected) + (1 if rng.random() < (expected % 1) else 0))
        if qty <= 0:
            continue
        player = await db.get(Player, listing.player_id)
        listing.qty -= qty
        listing.sold_total += qty
        adjust_coins(player, listing.price * qty)
        total_sold += qty
        await emit(db, world, "shop_sale",
                   {"good": listing.good_id, "qty": qty, "price": listing.price},
                   actor=player.id)
    return total_sold

"""Week 5: Crown licenses + sealed-bid auctions (glowdye monopoly arc)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import License, LicenseBid, Player, ScheduledEvent, World
from .common import GameError, adjust_coins, emit


async def player_has_license(db: AsyncSession, world: World, player_id: uuid.UUID, good_id: str) -> bool:
    row = await db.scalar(
        select(License).where(
            License.world_id == world.id,
            License.good_id == good_id,
            License.player_id == player_id,
            ~License.revoked,
        )
    )
    return row is not None


async def open_auction(db: AsyncSession, world: World, good_id: str, auction_id: str,
                       licenses: int, close_day_offset: int) -> None:
    db.add(ScheduledEvent(
        world_id=world.id, world_day=world.world_day + close_day_offset,
        kind="license_auction_close",
        params={"good": good_id, "auction_id": auction_id, "licenses": licenses},
    ))
    await emit(db, world, "auction_opened",
               {"good": good_id, "auction_id": auction_id, "licenses": licenses})


async def submit_bid(db: AsyncSession, world: World, player: Player, auction_id: str, amount: int) -> None:
    if world.current_week < 5:
        raise GameError("license auctions open in week 5")
    if amount <= 0:
        raise GameError("bid must be positive")
    if amount > player.coins:
        raise GameError("you cannot bid more than you hold")
    existing = await db.scalar(
        select(LicenseBid).where(
            LicenseBid.auction_id == auction_id, LicenseBid.player_id == player.id,
            LicenseBid.world_id == world.id,
        )
    )
    if existing:
        existing.amount = amount
    else:
        db.add(LicenseBid(world_id=world.id, auction_id=auction_id,
                          player_id=player.id, amount=amount))
    await emit(db, world, "license_bid", {"auction": auction_id, "amount": amount},
               actor=player.id)


async def close_auction(db: AsyncSession, world: World, good_id: str, auction_id: str,
                        n_licenses: int) -> list[dict]:
    """Sealed-bid, pay-your-bid, top-N win. Returns winners for the Crier."""
    bids = (
        await db.scalars(
            select(LicenseBid)
            .where(LicenseBid.world_id == world.id, LicenseBid.auction_id == auction_id)
            .order_by(LicenseBid.amount.desc(), LicenseBid.created_at)
        )
    ).all()
    winners = []
    for bid in bids[:n_licenses]:
        player = await db.get(Player, bid.player_id)
        if player.coins < bid.amount:
            continue  # spent it in the meantime; forfeit
        adjust_coins(player, -bid.amount)
        db.add(License(world_id=world.id, good_id=good_id, player_id=player.id,
                       source="auction", price_paid=bid.amount))
        winners.append({"merchant": player.merchant_name, "amount": bid.amount})
        await emit(db, world, "license_granted",
                   {"good": good_id, "auction": auction_id, "price": bid.amount},
                   actor=player.id)
    return winners


async def grant_license(db: AsyncSession, world: World, player_id: uuid.UUID, good_id: str) -> None:
    db.add(License(world_id=world.id, good_id=good_id, player_id=player_id, source="grant"))
    await emit(db, world, "license_granted", {"good": good_id, "source": "grant"},
               actor=player_id)


async def revoke_licenses(db: AsyncSession, world: World, good_id: str,
                          player_id: uuid.UUID | None = None) -> int:
    q = select(License).where(
        License.world_id == world.id, License.good_id == good_id, ~License.revoked
    )
    if player_id:
        q = q.where(License.player_id == player_id)
    rows = (await db.scalars(q)).all()
    for r in rows:
        r.revoked = True
    await emit(db, world, "license_revoked", {"good": good_id, "count": len(rows)})
    return len(rows)

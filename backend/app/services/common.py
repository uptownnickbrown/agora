"""Shared service helpers: money/inventory movement, event log, errors."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EconEvent, Inventory, Player, World


class GameError(Exception):
    """User-facing rule violation (mapped to HTTP 400)."""


async def emit(
    db: AsyncSession,
    world: World,
    kind: str,
    payload: dict | None = None,
    actor: uuid.UUID | None = None,
) -> None:
    db.add(
        EconEvent(
            world_id=world.id,
            world_day=world.world_day,
            kind=kind,
            actor_player_id=actor,
            payload=payload or {},
        )
    )


async def get_inventory(
    db: AsyncSession, world_id: uuid.UUID, player_id: uuid.UUID, good_id: str
) -> Inventory:
    row = await db.scalar(
        select(Inventory).where(
            Inventory.world_id == world_id,
            Inventory.player_id == player_id,
            Inventory.good_id == good_id,
        )
    )
    if row is None:
        row = Inventory(world_id=world_id, player_id=player_id, good_id=good_id, qty=0)
        db.add(row)
        await db.flush()
    return row


async def adjust_goods(
    db: AsyncSession, world_id: uuid.UUID, player: Player, good_id: str, delta: int
) -> None:
    """NPCs mint/absorb goods freely (that's what liquidity means); humans can't go negative."""
    inv = await get_inventory(db, world_id, player.id, good_id)
    if not player.is_npc and inv.qty + delta < 0:
        raise GameError(f"not enough {good_id} (have {inv.qty}, need {-delta})")
    inv.qty += delta
    if player.is_npc and inv.qty < 0:
        inv.qty = 0


def adjust_coins(player: Player, delta: int) -> None:
    if not player.is_npc and player.coins + delta < 0:
        raise GameError(f"not enough coins (have {player.coins}, need {-delta})")
    player.coins += delta
    if player.is_npc and player.coins < 0:
        player.coins = 0


def spend_effort(player: Player, amount: int) -> None:
    if player.effort < amount:
        raise GameError(f"not enough effort (have {player.effort}, need {amount})")
    player.effort -= amount

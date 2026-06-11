"""Week 7: Compacts — formal agreements with visible terms and NO enforcement.

Defection is always possible; that's the lesson. The detectors watch for
parallel pricing among members (cartel signature) and the Crier reports drama.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Compact, CompactMember, Player, World
from .common import GameError, emit

KINDS = {"price_accord", "supply_pact", "alliance"}


async def create_compact(db: AsyncSession, world: World, founder: Player,
                         name: str, kind: str, terms: dict) -> Compact:
    if world.current_week < 7:
        raise GameError("compacts open in week 7")
    if kind not in KINDS:
        raise GameError(f"kind must be one of {sorted(KINDS)}")
    compact = Compact(world_id=world.id, name=name[:120], kind=kind, terms=terms,
                      created_day=world.world_day)
    db.add(compact)
    await db.flush()
    db.add(CompactMember(compact_id=compact.id, player_id=founder.id,
                         joined_day=world.world_day))
    await emit(db, world, "compact_created", {"name": name, "kind": kind, "terms": terms},
               actor=founder.id)
    return compact


async def join_compact(db: AsyncSession, world: World, player: Player, compact_id: uuid.UUID) -> None:
    compact = await db.get(Compact, compact_id)
    if compact is None or compact.world_id != world.id or compact.dissolved_day is not None:
        raise GameError("compact not found")
    existing = await db.scalar(
        select(CompactMember).where(CompactMember.compact_id == compact_id,
                                    CompactMember.player_id == player.id)
    )
    if existing and existing.left_day is None:
        raise GameError("already a signatory")
    if existing:
        existing.left_day = None
        existing.joined_day = world.world_day
    else:
        db.add(CompactMember(compact_id=compact_id, player_id=player.id,
                             joined_day=world.world_day))
    await emit(db, world, "compact_joined", {"compact": str(compact_id)}, actor=player.id)


async def leave_compact(db: AsyncSession, world: World, player: Player, compact_id: uuid.UUID) -> None:
    member = await db.scalar(
        select(CompactMember).where(CompactMember.compact_id == compact_id,
                                    CompactMember.player_id == player.id,
                                    CompactMember.left_day.is_(None))
    )
    if member is None:
        raise GameError("not a signatory")
    member.left_day = world.world_day
    await emit(db, world, "compact_left", {"compact": str(compact_id)}, actor=player.id)
    remaining = (
        await db.scalars(
            select(CompactMember).where(CompactMember.compact_id == compact_id,
                                        CompactMember.left_day.is_(None))
        )
    ).all()
    if len(remaining) <= 1:
        compact = await db.get(Compact, compact_id)
        compact.dissolved_day = world.world_day
        await emit(db, world, "compact_dissolved", {"compact": str(compact_id)})


async def list_compacts(db: AsyncSession, world: World) -> list[dict]:
    compacts = (
        await db.scalars(select(Compact).where(Compact.world_id == world.id))
    ).all()
    out = []
    for c in compacts:
        members = (
            await db.scalars(
                select(CompactMember).where(CompactMember.compact_id == c.id,
                                            CompactMember.left_day.is_(None))
            )
        ).all()
        names = []
        for m in members:
            p = await db.get(Player, m.player_id)
            names.append(p.merchant_name)
        out.append({"id": str(c.id), "name": c.name, "kind": c.kind, "terms": c.terms,
                    "members": names, "created_day": c.created_day,
                    "dissolved_day": c.dissolved_day})
    return out

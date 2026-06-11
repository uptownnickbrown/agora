"""World lifecycle: create from template, roster join, week pacing, NPC seeding."""
from __future__ import annotations

import random
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    Course,
    NPCSchedule,
    Player,
    ScheduledEvent,
    Section,
    Team,
    User,
    World,
)
from .common import GameError, adjust_goods, emit

HOUSE_NAMES = ["Lantern", "Anchor", "Quill", "Bellows", "Compass", "Ledger"]

APTITUDE_GOODS = ["grain", "wool", "wood"]  # week-1 gatherables


async def create_world(
    db: AsyncSession,
    instructor: User,
    course_title: str,
    section_name: str,
    config: dict | None = None,
) -> World:
    course = Course(instructor_id=instructor.id, title=course_title,
                    institution_id=instructor.institution_id)
    db.add(course)
    await db.flush()
    section = Section(course_id=course.id, name=section_name)
    db.add(section)
    await db.flush()
    n = (config or {}).get("expected_students", 30)
    world = World(
        section_id=section.id,
        join_code=secrets.token_hex(4),
        state="onboarding",
        config={"template": T.TEMPLATE_VERSION, "pacing": "manual",
                "grade_weights": {"participation": 0.5, "mastery": 0.5},
                "fish_capacity": T.BALANCE["fish_capacity_per_student"] * max(8, n),
                **(config or {})},
        fish_stock=T.BALANCE["fish_stock_per_student"] * max(8, n),
    )
    db.add(world)
    await db.flush()

    for name in HOUSE_NAMES:
        db.add(Team(world_id=world.id, name=f"House {name}"))

    await _seed_npcs(db, world, expected_students=n)
    for beat in T.standard_script(n):
        db.add(ScheduledEvent(world_id=world.id, **beat))
    await emit(db, world, "world_created", {"template": T.TEMPLATE_VERSION})
    await db.flush()
    return world


async def _seed_npcs(db: AsyncSession, world: World, expected_students: int) -> None:
    npc = Player(world_id=world.id, merchant_name="The Countryside", is_npc=True, coins=0)
    db.add(npc)
    await db.flush()
    n = max(8, expected_students)
    for good_id, (supply_f, demand_f) in T.NPC_FLOWS.items():
        good = T.GOODS[good_id]
        if supply_f > 0:
            lo, hi = T.NPC_BANDS["default_supply"]
            db.add(NPCSchedule(
                world_id=world.id, npc_player_id=npc.id, good_id=good_id, side="sell",
                p_low=round(good.anchor * lo), p_high=round(good.anchor * hi),
                qty_per_day=max(2, round(n * supply_f)),
            ))
        if demand_f > 0:
            lo, hi = T.NPC_BANDS["demand_overrides"].get(
                good_id, T.NPC_BANDS["default_demand"]
            )
            db.add(NPCSchedule(
                world_id=world.id, npc_player_id=npc.id, good_id=good_id, side="buy",
                p_low=round(good.anchor * lo), p_high=round(good.anchor * hi),
                qty_per_day=max(2, round(n * demand_f)),
            ))


async def join_world(db: AsyncSession, user: User, join_code: str) -> Player:
    world = await db.scalar(select(World).where(World.join_code == join_code))
    if world is None:
        raise GameError("no world with that join code")
    if world.state in ("epilogue", "archived"):
        raise GameError("this world has ended")
    existing = await db.scalar(
        select(Player).where(Player.world_id == world.id, Player.user_id == user.id)
    )
    if existing:
        return existing

    # Deliberately unbalanced endowments: heavy in one good + a gathering
    # aptitude, so Week 1 trade is obviously valuable (spec §6 wk1).
    n_players = await db.scalar(
        select(func.count(Player.id)).where(Player.world_id == world.id, ~Player.is_npc)
    ) or 0
    aptitude = APTITUDE_GOODS[n_players % len(APTITUDE_GOODS)]
    teams = (await db.scalars(select(Team).where(Team.world_id == world.id))).all()
    team = teams[n_players % len(teams)] if teams else None

    player = Player(
        world_id=world.id,
        user_id=user.id,
        team_id=team.id if team else None,
        merchant_name=user.display_name,
        coins=T.BALANCE["starting_coins"],
        effort=T.BALANCE["effort_per_day"],
        aptitude_good=aptitude,
        last_active_day=world.world_day,
    )
    db.add(player)
    await db.flush()
    await adjust_goods(db, world.id, player, aptitude, T.BALANCE["starting_endowment_qty"])
    await emit(db, world, "player_joined", {"merchant": player.merchant_name}, actor=player.id)
    return player


async def get_world(db: AsyncSession, world_id: uuid.UUID) -> World:
    world = await db.get(World, world_id)
    if world is None:
        raise GameError("world not found")
    return world


async def advance_week(db: AsyncSession, world: World) -> None:
    if world.current_week >= 7:
        raise GameError("already in week 7 — end the world instead")
    world.current_week += 1
    if world.state == "onboarding":
        world.state = "active"
    await emit(db, world, "week_advanced", {"week": world.current_week})


async def set_state(db: AsyncSession, world: World, state: str) -> None:
    allowed = {"draft", "onboarding", "active", "tournament", "epilogue", "archived"}
    if state not in allowed:
        raise GameError(f"unknown state {state}")
    world.state = state
    await emit(db, world, "world_state", {"state": state})


def good_unlocked(world: World, good_id: str) -> bool:
    good = T.GOODS.get(good_id)
    return good is not None and good.unlock_week <= world.current_week


async def instructor_for_world(db: AsyncSession, world: World) -> uuid.UUID:
    section = await db.get(Section, world.section_id)
    course = await db.get(Course, section.course_id)
    return course.instructor_id

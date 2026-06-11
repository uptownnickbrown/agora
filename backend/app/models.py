"""Core persistent entities (first cut — spec §12.5, DECISIONS.md).

Tenancy invariant: every World-scoped row carries world_id and every query
filters by it. Def-tables (GoodDef, …) are template-scoped and shared across
Worlds. Money is integer coppers; quantities integer units; no floats in
economic state. The append-only econ_events table is the source of truth;
the rest are projections.

Entities not yet here (CraftJob, Shop, Compact, TutorCheck, Puzzle*, …) arrive
with the feature that needs them — see docs/SPEC.md §12.5 for the full list.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# -- tenancy hierarchy: Institution -> Course -> Section -> World ------------

class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id"))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # optional; magic-link primary
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Course(TimestampMixin, Base):
    __tablename__ = "courses"
    id: Mapped[uuid.UUID] = uuid_pk()
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"))
    instructor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))


class Section(TimestampMixin, Base):
    __tablename__ = "sections"
    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"))
    name: Mapped[str] = mapped_column(String(120))


class WorldState(enum.Enum):
    draft = "draft"
    onboarding = "onboarding"
    active = "active"
    tournament = "tournament"
    epilogue = "epilogue"
    archived = "archived"


class World(TimestampMixin, Base):
    """One section's isolated economy. Owns its logical clock."""

    __tablename__ = "worlds"
    id: Mapped[uuid.UUID] = uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sections.id"), unique=True)
    state: Mapped[WorldState] = mapped_column(Enum(WorldState), default=WorldState.draft)
    join_code: Mapped[str] = mapped_column(String(12), unique=True)
    current_week: Mapped[int] = mapped_column(Integer, default=0)  # 0 = pre-launch
    world_day: Mapped[int] = mapped_column(Integer, default=0)     # logical clock
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    config: Mapped[dict] = mapped_column(JSON, default=dict)       # template knobs


class Team(TimestampMixin, Base):
    """Light affiliation (DECISIONS.md #6): cosmetic until the Week 7 tournament."""

    __tablename__ = "teams"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("world_id", "user_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    merchant_name: Mapped[str] = mapped_column(String(80))
    coins: Mapped[int] = mapped_column(BigInteger, default=0)  # integer coppers
    effort: Mapped[int] = mapped_column(Integer, default=0)    # daily action points
    is_npc: Mapped[bool] = mapped_column(Boolean, default=False)


# -- template-scoped definitions ---------------------------------------------

class GoodDef(Base):
    __tablename__ = "good_defs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "grain"
    tier: Mapped[str] = mapped_column(String(20))  # raw | processed | finished
    display_name: Mapped[str] = mapped_column(String(80))
    unlock_week: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


# -- markets ------------------------------------------------------------------

class OrderSide(enum.Enum):
    buy = "buy"
    sell = "sell"


class DbOrder(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_book", "world_id", "good_id", "status"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    good_id: Mapped[str] = mapped_column(ForeignKey("good_defs.id"))
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide))
    qty: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    price: Mapped[int | None] = mapped_column(Integer)  # None = market order
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|filled|cancelled|expired
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DbTrade(TimestampMixin, Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_tape", "world_id", "good_id", "created_at"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    good_id: Mapped[str] = mapped_column(ForeignKey("good_defs.id"))
    buyer_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    seller_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)


class PriceSnapshot(Base):
    """Official daily-close OHLCV per good (the Crier's numbers)."""

    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("world_id", "good_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    good_id: Mapped[str] = mapped_column(ForeignKey("good_defs.id"))
    world_day: Mapped[int] = mapped_column(Integer)
    open: Mapped[int | None] = mapped_column(Integer)
    high: Mapped[int | None] = mapped_column(Integer)
    low: Mapped[int | None] = mapped_column(Integer)
    close: Mapped[int | None] = mapped_column(Integer)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    unfilled_demand: Mapped[int] = mapped_column(Integer, default=0)


class Inventory(Base):
    __tablename__ = "inventories"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "good_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    good_id: Mapped[str] = mapped_column(ForeignKey("good_defs.id"))
    qty: Mapped[int] = mapped_column(Integer, default=0)


# -- event-sourcing-lite -------------------------------------------------------

class EconEvent(Base):
    """Append-only log of every economically meaningful action. The truth."""

    __tablename__ = "econ_events"
    __table_args__ = (Index("ix_econ_events_world_seq", "world_id", "id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    kind: Mapped[str] = mapped_column(String(40))  # order_placed | trade | intervention | ...
    actor_player_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("players.id"))
    payload: Mapped[dict] = mapped_column(JSON)


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # drought | festival | price_ceiling | ...
    params: Mapped[dict] = mapped_column(JSON)
    scheduled_world_day: Mapped[int | None] = mapped_column(Integer)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crier_copy: Mapped[str | None] = mapped_column(Text)  # the diegetic announcement


# -- pedagogy layer (skeleton; grows in Phase 1) -------------------------------

class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "ch3-lo2"
    chapter: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class MasteryEstimate(Base):
    __tablename__ = "mastery_estimates"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "lo_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    lo_id: Mapped[str] = mapped_column(ForeignKey("learning_objectives.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-1000 fixed-point
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

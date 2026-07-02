"""Persistent entities (spec §12.5, DECISIONS.md).

Conventions:
- Tenancy: every World-scoped row carries world_id; queries always filter by it.
- Money is integer coppers, quantities integer units. No floats in economic state.
- Template definitions (goods tree, facility defs, recipes, question bank,
  achievements, cosmetics) live in code (app/template.py, app/pedagogy/bank.py)
  and are referenced by string id — the DB stores instances only.
- econ_events is the append-only source of truth; other tables are projections.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
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

BigIntPK = BigInteger().with_variant(Integer, "sqlite")


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# -- identity & tenancy -------------------------------------------------------

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
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_instructor: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MagicToken(TimestampMixin, Base):
    __tablename__ = "magic_tokens"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Course(TimestampMixin, Base):
    __tablename__ = "courses"
    id: Mapped[uuid.UUID] = uuid_pk()
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id"))
    instructor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))


class Section(TimestampMixin, Base):
    __tablename__ = "sections"
    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"))
    name: Mapped[str] = mapped_column(String(120))


# World.state: draft | onboarding | active | tournament | epilogue | archived
class World(TimestampMixin, Base):
    """One section's isolated economy with its own logical clock."""

    __tablename__ = "worlds"
    id: Mapped[uuid.UUID] = uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sections.id"), unique=True)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    join_code: Mapped[str] = mapped_column(String(12), unique=True)
    current_week: Mapped[int] = mapped_column(Integer, default=1)
    world_day: Mapped[int] = mapped_column(Integer, default=0)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    config: Mapped[dict] = mapped_column(JSON, default=dict)        # knobs, grade weights
    market_rules: Mapped[dict] = mapped_column(JSON, default=dict)  # ceilings/floors/taxes
    smog: Mapped[int] = mapped_column(Integer, default=0)
    fish_stock: Mapped[int] = mapped_column(Integer, default=1000)
    fishing_rules: Mapped[dict] = mapped_column(JSON, default=dict)  # quota, closed_season


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    banner: Mapped[str] = mapped_column(String(40), default="plain")


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("world_id", "user_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # None for NPCs
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    merchant_name: Mapped[str] = mapped_column(String(80))
    coins: Mapped[int] = mapped_column(BigInteger, default=0)
    effort: Mapped[int] = mapped_column(Integer, default=20)
    aptitude_good: Mapped[str | None] = mapped_column(String(40))
    is_npc: Mapped[bool] = mapped_column(Boolean, default=False)
    bankrupt_resets: Mapped[int] = mapped_column(Integer, default=0)
    last_active_day: Mapped[int] = mapped_column(Integer, default=0)


# -- economy: holdings, markets ----------------------------------------------

class Inventory(Base):
    __tablename__ = "inventories"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "good_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    qty: Mapped[int] = mapped_column(Integer, default=0)


# Order.status: open | filled | cancelled | expired
class DbOrder(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_book", "world_id", "good_id", "status"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    side: Mapped[str] = mapped_column(String(4))  # buy | sell
    qty: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)  # limit price (market orders never rest)
    status: Mapped[str] = mapped_column(String(12), default="open")
    placed_day: Mapped[int] = mapped_column(Integer)
    expires_day: Mapped[int] = mapped_column(Integer)  # expires at close of this day
    seq: Mapped[int] = mapped_column(BigInteger, default=0)  # time priority within world


class DbTrade(TimestampMixin, Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_tape", "world_id", "good_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    buyer_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    seller_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    world_day: Mapped[int] = mapped_column(Integer)


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("world_id", "good_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    world_day: Mapped[int] = mapped_column(Integer)
    open: Mapped[int | None] = mapped_column(Integer)
    high: Mapped[int | None] = mapped_column(Integer)
    low: Mapped[int | None] = mapped_column(Integer)
    close: Mapped[int | None] = mapped_column(Integer)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    unfilled_demand: Mapped[int] = mapped_column(Integer, default=0)
    suppressed_asks: Mapped[int] = mapped_column(Integer, default=0)


class NPCSchedule(Base):
    """Piecewise-linear supply/demand schedule driving one NPC trader's flow.
    Interventions work by mutating price_mult / qty_mult (optionally temporarily)."""

    __tablename__ = "npc_schedules"
    __table_args__ = (UniqueConstraint("world_id", "good_id", "side"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    npc_player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    good_id: Mapped[str] = mapped_column(String(40))
    side: Mapped[str] = mapped_column(String(4))
    p_low: Mapped[int] = mapped_column(Integer)
    p_high: Mapped[int] = mapped_column(Integer)
    qty_per_day: Mapped[int] = mapped_column(Integer)
    price_mult: Mapped[float] = mapped_column(Float, default=1.0)
    qty_mult: Mapped[float] = mapped_column(Float, default=1.0)
    revert_day: Mapped[int | None] = mapped_column(Integer)  # auto-revert multipliers
    paused: Mapped[bool] = mapped_column(Boolean, default=False)


# -- production ----------------------------------------------------------------

class Facility(TimestampMixin, Base):
    __tablename__ = "facilities"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # FacilityDef id in template
    tier: Mapped[int] = mapped_column(Integer, default=1)
    workers: Mapped[int] = mapped_column(Integer, default=0)  # hired NPC labor
    scrubber: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ShopListing(TimestampMixin, Base):
    """Posted-price retail channel; NPC retail demand sampled at daily close."""

    __tablename__ = "shop_listings"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "good_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer, default=0)  # stocked into the shop
    sold_total: Mapped[int] = mapped_column(Integer, default=0)


class GuildLoan(TimestampMixin, Base):
    __tablename__ = "guild_loans"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    principal: Mapped[int] = mapped_column(Integer)
    outstanding: Mapped[int] = mapped_column(Integer)
    rate_bp_per_day: Mapped[int] = mapped_column(Integer, default=20)  # basis points


# -- week 5/7 market structure --------------------------------------------------

class License(TimestampMixin, Base):
    __tablename__ = "licenses"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    good_id: Mapped[str] = mapped_column(String(40))
    player_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("players.id"))
    source: Mapped[str] = mapped_column(String(20), default="auction")  # auction | grant
    price_paid: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class LicenseBid(TimestampMixin, Base):
    __tablename__ = "license_bids"
    __table_args__ = (UniqueConstraint("auction_id", "player_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    auction_id: Mapped[str] = mapped_column(String(60))  # e.g. "glowdye-1"
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    amount: Mapped[int] = mapped_column(Integer)


class Compact(TimestampMixin, Base):
    """Week 7: visible terms, zero enforcement. Defection is always possible."""

    __tablename__ = "compacts"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(30))  # price_accord | supply | alliance
    terms: Mapped[dict] = mapped_column(JSON)
    created_day: Mapped[int] = mapped_column(Integer)
    dissolved_day: Mapped[int | None] = mapped_column(Integer)


class CompactMember(Base):
    __tablename__ = "compact_members"
    __table_args__ = (UniqueConstraint("compact_id", "player_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    compact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compacts.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    joined_day: Mapped[int] = mapped_column(Integer)
    left_day: Mapped[int | None] = mapped_column(Integer)


# -- events, interventions, narration -------------------------------------------

class EconEvent(Base):
    __tablename__ = "econ_events"
    __table_args__ = (Index("ix_econ_events_world", "world_id", "id"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"))
    world_day: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    kind: Mapped[str] = mapped_column(String(40), index=True)
    actor_player_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("players.id"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ScheduledEvent(Base):
    """World-day-scheduled script beats and instructor-scheduled interventions."""

    __tablename__ = "scheduled_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    world_day: Mapped[int] = mapped_column(Integer)
    crier_copy: Mapped[str | None] = mapped_column(Text)


class CrierPost(TimestampMixin, Base):
    __tablename__ = "crier_posts"
    __table_args__ = (Index("ix_crier_world_day", "world_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"))
    world_day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))  # market_report | news | event
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)


class DetectedMoment(TimestampMixin, Base):
    __tablename__ = "detected_moments"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10), default="info")  # info|notable|alert
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    endorsed: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailLog(TimestampMixin, Base):
    """Audit trail for outbound email (digests, magic links, alerts).

    Idempotency for the weekly digest lives in world.config (digest_sent_week);
    this table is audit + dev-mode inspection, so re-sends are allowed.
    """
    __tablename__ = "email_log"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worlds.id"), index=True, nullable=True)
    to_email: Mapped[str] = mapped_column(String(320))
    kind: Mapped[str] = mapped_column(String(24))  # digest | magic_link | alert
    ref: Mapped[str] = mapped_column(String(40), default="")  # e.g. "week:3"
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(12))  # sent | failed | console
    provider_id: Mapped[str] = mapped_column(String(80), default="")
    body_text: Mapped[str] = mapped_column(Text, default="")  # console mode only


# -- fun layer -------------------------------------------------------------------

class PuzzleAttempt(Base):
    __tablename__ = "puzzle_attempts"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    guesses: Mapped[list] = mapped_column(JSON, default=list)
    solved: Mapped[bool] = mapped_column(Boolean, default=False)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)


class FishingCatch(TimestampMixin, Base):
    __tablename__ = "fishing_catches"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    fish_qty: Mapped[int] = mapped_column(Integer)
    weight: Mapped[int] = mapped_column(Integer)  # decigrams of glory
    trophy: Mapped[str | None] = mapped_column(String(60))


class HaggleSession(Base):
    """One caravan visitor per merchant per day: a hidden reservation price,
    up to three quotes, and a lesson about surplus either way."""

    __tablename__ = "haggle_sessions"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    good_id: Mapped[str] = mapped_column(String(24))
    side: Mapped[str] = mapped_column(String(12))  # npc_buys | npc_sells
    qty: Mapped[int] = mapped_column(Integer)
    reservation: Mapped[int] = mapped_column(Integer)
    visitor: Mapped[str] = mapped_column(String(60))
    portrait: Mapped[str] = mapped_column(String(24))
    offers: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String(12), default="open")
    accepted_price: Mapped[int | None] = mapped_column(Integer)


class Streak(Base):
    __tablename__ = "streaks"
    __table_args__ = (UniqueConstraint("player_id", "kind"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # login | puzzle
    count: Mapped[int] = mapped_column(Integer, default=0)
    best: Mapped[int] = mapped_column(Integer, default=0)
    last_day: Mapped[int] = mapped_column(Integer, default=0)


class PlayerAchievement(Base):
    __tablename__ = "player_achievements"
    __table_args__ = (UniqueConstraint("player_id", "achievement_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    achievement_id: Mapped[str] = mapped_column(String(60))
    world_day: Mapped[int] = mapped_column(Integer)


class PlayerCosmetic(Base):
    __tablename__ = "player_cosmetics"
    __table_args__ = (UniqueConstraint("player_id", "cosmetic_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    cosmetic_id: Mapped[str] = mapped_column(String(60))
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)


class MerchantRun(Base):
    """Week 1 'Traveling Merchant' onboarding minigame instance + result."""

    __tablename__ = "merchant_runs"
    __table_args__ = (UniqueConstraint("world_id", "player_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    seed: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    profit: Mapped[int] = mapped_column(Integer, default=0)


# -- pedagogy --------------------------------------------------------------------

class CheckAttempt(TimestampMixin, Base):
    __tablename__ = "check_attempts"
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(60))
    world_day: Mapped[int] = mapped_column(Integer)
    answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[int] = mapped_column(Integer)  # 0-100
    feedback: Mapped[str] = mapped_column(Text, default="")


class MasteryEstimate(Base):
    __tablename__ = "mastery_estimates"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "lo_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    lo_id: Mapped[str] = mapped_column(String(40))
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-1000 fixed point
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class TutorMessage(TimestampMixin, Base):
    __tablename__ = "tutor_messages"
    __table_args__ = (Index("ix_tutor_msgs", "world_id", "player_id", "id"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"))
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"))
    role: Mapped[str] = mapped_column(String(10))  # user | tutor
    content: Mapped[str] = mapped_column(Text)
    world_day: Mapped[int] = mapped_column(Integer)


# -- analytics projections --------------------------------------------------------

class PlayerDayStat(Base):
    __tablename__ = "player_day_stats"
    __table_args__ = (UniqueConstraint("world_id", "player_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("players.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    coins: Mapped[int] = mapped_column(BigInteger)
    net_worth: Mapped[int] = mapped_column(BigInteger)
    participation: Mapped[int] = mapped_column(Integer, default=0)  # points earned today


class WorldDayStat(Base):
    __tablename__ = "world_day_stats"
    __table_args__ = (UniqueConstraint("world_id", "world_day"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id"), index=True)
    world_day: Mapped[int] = mapped_column(Integer)
    gini_bp: Mapped[int] = mapped_column(Integer, default=0)  # Gini in basis points
    total_volume: Mapped[int] = mapped_column(Integer, default=0)
    active_players: Mapped[int] = mapped_column(Integer, default=0)
    smog: Mapped[int] = mapped_column(Integer, default=0)
    fish_stock: Mapped[int] = mapped_column(Integer, default=0)

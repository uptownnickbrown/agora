"""The Monday Brief: a weekly email digest so instructors never have to log in.

Flow: advance_week stamps world.config["digest_due_week"]; the worker's
email_sweep cron calls process_due_digests, which builds the brief (lecture
playbook + class summary + at-risk students), emails the instructor, and
stamps digest_sent_week. The stamp, not email_log, is the idempotency record.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import Course, Player, Section, User, World
from ..pedagogy.grades import gradebook, gradebook_csv
from ..pedagogy.playbook import build_playbook
from .email import EmailError, EmailMessage, markdown_to_html, send_logged

INACTIVE_DAYS = 5  # roster flag threshold, same as the dashboard
LOW_MASTERY = 0.4


async def _course_for_world(db: AsyncSession, world: World) -> Course:
    section = await db.get(Section, world.section_id)
    return await db.get(Course, section.course_id)


async def build_digest(db: AsyncSession, world: World, week: int) -> EmailMessage:
    """Read-only assembly of the weekly brief. No sends, no writes."""
    settings = get_settings()
    course = await _course_for_world(db, world)
    instructor = await db.get(User, course.instructor_id)

    pb = await build_playbook(db, world, week)
    rows = await gradebook(db, world)

    lines: list[str] = []
    if rows:
        avg_part = sum(r["participation"] for r in rows) / len(rows)
        avg_mastery = sum(r["mastery"] for r in rows) / len(rows)
        lines += ["## Class at a glance",
                  f"- {len(rows)} students enrolled",
                  f"- Average participation: {avg_part:.0%}",
                  f"- Average mastery: {avg_mastery:.0%}", ""]

    at_risk: list[str] = []
    players = {r["merchant"]: r for r in rows}
    roster = (
        await db.scalars(select(Player).where(Player.world_id == world.id,
                                              ~Player.is_npc))
    ).all()
    for p in roster:
        reasons = []
        if world.world_day - p.last_active_day >= INACTIVE_DAYS:
            reasons.append(f"inactive {world.world_day - p.last_active_day} days")
        row = players.get(p.merchant_name)
        if row and world.current_week >= 2 and row["mastery"] < LOW_MASTERY:
            reasons.append(f"mastery {row['mastery']:.0%}")
        if reasons:
            email = row["email"] if row else ""
            at_risk.append(f"- **{p.merchant_name}**"
                           + (f" ({email})" if email else "")
                           + ": " + ", ".join(reasons))
    if at_risk:
        lines += ["## Students who may need a nudge", *at_risk, ""]

    base = settings.app_base_url.rstrip("/")
    lines += [f"[Open the instructor dashboard]({base}/#/{world.id})", "",
              "The current gradebook is attached as CSV (imports directly "
              "into most LMS gradebooks).", ""]

    md = "\n".join([pb["markdown"], ""] + lines)
    csv_text = await gradebook_csv(db, world)
    return EmailMessage(
        to=instructor.email,
        subject=f"Agora Monday Brief — {course.title}, Week {week} in review",
        text=md,
        html=markdown_to_html(md),
        attachments=[(f"agora-gradebook-week{week}.csv", "text/csv", csv_text)],
    )


async def process_due_digests(factory) -> int:
    """Scan live worlds for digests due, send, stamp. Idempotent and
    per-world isolated, mirroring the daily-close worker job."""
    import logging

    sent = 0
    async with factory() as db:
        world_ids = list(
            await db.scalars(
                select(World.id).where(
                    World.state.in_(["onboarding", "active", "tournament",
                                     "epilogue"]))
            )
        )
    for wid in world_ids:
        try:
            sent += await _process_one(factory, wid)
        except Exception:  # noqa: BLE001 - isolate per-world failures
            logging.getLogger("agora.worker").exception(
                "digest failed for world %s", wid)
    return sent


async def _process_one(factory, wid) -> int:
    # Session 1: read-only — decide, then build (may take ~30s with LLM polish).
    async with factory() as db:
        world = await db.get(World, wid)
        config = world.config or {}
        due = config.get("digest_due_week") or 0
        if due <= config.get("digest_sent_week", 0):
            return 0
        if (world.config or {}).get("is_demo"):
            msg = None  # demo worlds never email anyone
        elif not config.get("email_digest", True):
            msg = None  # opted out: stamp without sending so no backlog grows
        else:
            msg = await build_digest(db, world, due)

    # Session 2: send (no DB session held), then stamp + log atomically.
    async with factory() as db:
        async with db.begin():
            world = await db.get(World, wid, with_for_update=True)
            config = world.config or {}
            if due <= config.get("digest_sent_week", 0):
                return 0  # raced with a manual send
            if msg is not None:
                try:
                    await send_logged(db, msg, kind="digest", world_id=world.id,
                                      ref=f"week:{due}")
                except EmailError:
                    return 0  # logged as failed; retried on the next sweep
            world.config = {**config, "digest_sent_week": due}
    return 1 if msg is not None else 0

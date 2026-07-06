"""The Monday Brief: a weekly email digest so instructors never have to log in.

Flow: advance_week stamps world.config["digest_due_week"]; the worker's
email_sweep cron calls process_due_digests, which builds the brief (lecture
playbook + class summary + at-risk students), emails the instructor, and
stamps digest_sent_week. The stamp, not email_log, is the idempotency record.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..config import get_settings
from ..models import (
    Course,
    MasteryEstimate,
    Player,
    PriceSnapshot,
    Section,
    User,
    World,
)
from ..pedagogy.bank import LEARNING_OBJECTIVES
from ..pedagogy.grades import gradebook, gradebook_csv
from ..pedagogy.playbook import build_playbook
from .email import EmailError, EmailMessage, brief_shell, markdown_to_html, send_logged

INACTIVE_DAYS = 5  # roster flag threshold, same as the dashboard
LOW_MASTERY = 0.4

# Same-day builds are identical (playbook + stats change at the close), and
# the Opus polish is the expensive part — so preview clicks and the send
# sweep share one build per (world, week, day). In-process, deliberately.
_CACHE: dict[tuple, EmailMessage] = {}


async def _course_for_world(db: AsyncSession, world: World) -> Course:
    section = await db.get(Section, world.section_id)
    return await db.get(Course, section.course_id)


async def _week_mover(db: AsyncSession, world: World, week: int) -> str | None:
    """The week's biggest price story: '**Bread** climbed 42% to 255.'"""
    day_lo = (week - 1) * T.DAYS_PER_WEEK + 1
    day_hi = week * T.DAYS_PER_WEEK
    snaps = (
        await db.scalars(
            select(PriceSnapshot).where(
                PriceSnapshot.world_id == world.id,
                PriceSnapshot.world_day.between(day_lo, day_hi),
                PriceSnapshot.close.is_not(None),
            ).order_by(PriceSnapshot.world_day)
        )
    ).all()
    series: dict[str, list[int]] = {}
    for s in snaps:
        series.setdefault(s.good_id, []).append(s.close)
    best: tuple[float, str, int, int] | None = None
    for good, closes in series.items():
        if len(closes) < 2 or closes[0] == 0:
            continue
        pct = (closes[-1] - closes[0]) / closes[0]
        if best is None or abs(pct) > abs(best[0]):
            best = (pct, good, closes[0], closes[-1])
    if best is None or abs(best[0]) < 0.08:
        return None
    pct, good, first, last = best
    verb = "climbed" if pct > 0 else "fell"
    name = T.GOODS[good].name if good in T.GOODS else good
    return f"**{name}** {verb} {abs(pct):.0%} this week ({first} → {last})"


async def _weakest_objectives(db: AsyncSession, world: World, n: int = 2) -> list[str]:
    """Class-average mastery per objective, lowest first — lecture fuel.
    Enrolled students only; demo visitors don't tilt the class picture."""
    rows = (
        await db.scalars(
            select(MasteryEstimate)
            .join(Player, Player.id == MasteryEstimate.player_id)
            .where(MasteryEstimate.world_id == world.id,
                   ~Player.is_npc, ~Player.is_visitor)
        )
    ).all()
    sums: dict[str, list[int]] = {}
    for m in rows:
        sums.setdefault(m.lo_id, []).append(m.score)
    avgs = sorted(
        ((sum(v) / len(v) / 10, lo) for lo, v in sums.items()
         if lo in LEARNING_OBJECTIVES and len(v) >= 2
         and LEARNING_OBJECTIVES[lo].week <= world.current_week),
        key=lambda t: t[0])
    return [f"{LEARNING_OBJECTIVES[lo].short} ({pct:.0f}%)"
            for pct, lo in avgs[:n] if pct < 65]


async def build_digest(db: AsyncSession, world: World, week: int) -> EmailMessage:
    """Read-only assembly of the weekly brief. No sends, no writes."""
    cache_key = (world.id, week, world.world_day)
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    settings = get_settings()
    course = await _course_for_world(db, world)
    instructor = await db.get(User, course.instructor_id)

    pb = await build_playbook(db, world, week)
    rows = await gradebook(db, world)
    mover = await _week_mover(db, world, week)
    weak = await _weakest_objectives(db, world)

    at_risk: list[str] = []
    players = {r["merchant"]: r for r in rows}
    roster = (
        await db.scalars(select(Player).where(Player.world_id == world.id,
                                              ~Player.is_npc,
                                              ~Player.is_visitor))
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

    # The sixty-second version rides on top: the professor who reads nothing
    # else still walks into Monday knowing the story, the gap, and the risk.
    fast: list[str] = ["## The sixty-second version"]
    if mover:
        fast.append(f"- {mover}.")
    if rows:
        avg_part = sum(r["participation"] for r in rows) / len(rows)
        avg_mastery = sum(r["mastery"] for r in rows) / len(rows)
        fast.append(f"- {len(rows)} students · participation {avg_part:.0%} · "
                    f"mastery {avg_mastery:.0%}.")
    if weak:
        fast.append(f"- The tutor's weakest spots: {', '.join(weak)} — "
                    "discussion questions below are aimed at them.")
    if at_risk:
        fast.append(f"- {len(at_risk)} student{'s' if len(at_risk) != 1 else ''} "
                    "may need a nudge (names at the bottom).")
    fast.append("")

    tail: list[str] = []
    if at_risk:
        tail += ["## Students who may need a nudge", *at_risk, ""]
    tail += ["The current gradebook is attached as CSV (imports directly "
             "into most LMS gradebooks).", ""]

    md = "\n".join(fast + [pb["markdown"], ""] + tail)
    csv_text = await gradebook_csv(db, world)
    base = settings.app_base_url.rstrip("/")
    subject = f"Monday Brief — {course.title}, Week {week}"
    if mover:
        subject += ": " + (mover.replace("**", "").split(" this week")[0]
                           .replace("climbed", "up").replace("fell", "down"))
    msg = EmailMessage(
        to=instructor.email,
        subject=subject,
        text=md,
        html=brief_shell(course.title, week, markdown_to_html(md),
                         f"{base}/#/{world.id}"),
        attachments=[(f"agora-gradebook-week{week}.csv", "text/csv", csv_text)],
    )
    _CACHE[cache_key] = msg
    if len(_CACHE) > 200:  # a term's worth; drop the oldest wholesale
        _CACHE.clear()
        _CACHE[cache_key] = msg
    return msg


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

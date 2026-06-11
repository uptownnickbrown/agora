"""Professor Pip — the LLM-backed tutor (spec §9).

Model tiering (DECISIONS.md #7): Haiku for classification, Sonnet for tutoring
conversations and free-response grading, Opus for playbooks (see playbook.py).
Every LLM path degrades gracefully to canned content when no API key is
configured or the per-World daily budget is exhausted.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import (
    CheckAttempt,
    EconEvent,
    Inventory,
    MasteryEstimate,
    Player,
    PriceSnapshot,
    TutorMessage,
    World,
)
from ..services.common import GameError, emit
from .bank import LEARNING_OBJECTIVES, QUESTIONS, questions_for_context, questions_for_week

PIP_SYSTEM = """You are Professor Pip, a know-it-all market pigeon who tutors \
students inside Agora, a multiplayer economic simulation for an intro \
microeconomics course. You wear a tiny waistcoat and a monocle and you are \
delighted by markets.

Rules you never break:
- Teach economics through what is happening in the student's own game. Be \
Socratic by default: guide with questions before giving answers.
- Stay in character: warm, witty, a little smug, never naggy. Keep replies \
under 150 words.
- NEVER place trades, name exact prices to buy/sell at, or otherwise play the \
game for the student. Help them reason; don't hand them the answer key to the \
market.
- NEVER reveal other students' private information or upcoming instructor \
interventions.
- If asked about non-economics topics, redirect kindly: "ask your professor — \
and what a fine question to ask."
"""

DAILY_TOKEN_BUDGET = 60_000  # per World per day, rough cost ceiling
PER_STUDENT_DAILY_MSGS = 30

CANNED_REPLIES = [
    "Coo! My feathers are ruffled and my thoughts are scattered today (the "
    "connection to the Great Library is down). Try the price charts — they "
    "rarely lie. What do you notice about the last three days?",
    "A fine question. Alas, my monocle is fogged at the moment. While I "
    "polish it: check the order book. Where are the bids piling up, and what "
    "might that tell you?",
]

_LLM_USAGE: dict[str, int] = {}  # f"{world_id}:{day}" -> tokens (in-process budget)


def _budget_key(world: World) -> str:
    return f"{world.id}:{world.world_day}"


def _budget_remaining(world: World) -> int:
    return DAILY_TOKEN_BUDGET - _LLM_USAGE.get(_budget_key(world), 0)


def _record_usage(world: World, tokens: int) -> None:
    key = _budget_key(world)
    _LLM_USAGE[key] = _LLM_USAGE.get(key, 0) + tokens


def _client():
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        return None


async def _student_context(db: AsyncSession, world: World, player: Player) -> str:
    """Assemble compact game context for the tutor (volatile — goes AFTER the
    cached system prompt, never inside it)."""
    events = (
        await db.scalars(
            select(EconEvent)
            .where(EconEvent.world_id == world.id, EconEvent.actor_player_id == player.id)
            .order_by(EconEvent.id.desc()).limit(10)
        )
    ).all()
    recent = "; ".join(f"{e.kind}:{e.payload}" for e in reversed(events))[:800]
    invs = (
        await db.scalars(
            select(Inventory).where(Inventory.world_id == world.id,
                                    Inventory.player_id == player.id, Inventory.qty > 0)
        )
    ).all()
    holdings = ", ".join(f"{i.qty} {i.good_id}" for i in invs) or "nothing"
    snaps = (
        await db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.world_id == world.id,
                   PriceSnapshot.world_day == world.world_day - 1,
                   PriceSnapshot.close.is_not(None))
        )
    ).all()
    prices = ", ".join(f"{s.good_id}={s.close}" for s in snaps) or "no closes yet"
    week_los = "; ".join(lo.text for lo in LEARNING_OBJECTIVES.values()
                         if lo.week == world.current_week)
    mastery = (
        await db.scalars(
            select(MasteryEstimate).where(MasteryEstimate.world_id == world.id,
                                          MasteryEstimate.player_id == player.id)
        )
    ).all()
    weak = sorted(mastery, key=lambda m: m.score)[:3]
    weak_txt = ", ".join(f"{m.lo_id}({m.score / 10:.0f}%)" for m in weak) or "none yet"
    rules = world.market_rules or {}
    return (
        f"[GAME CONTEXT — week {world.current_week}, day {world.world_day}] "
        f"Student: {player.merchant_name}, {player.coins} coins, effort {player.effort}. "
        f"Holdings: {holdings}. Recent actions: {recent or 'none'}. "
        f"Yesterday's closes: {prices}. Active market rules: {rules}. "
        f"This week's objectives: {week_los}. Weakest mastery: {weak_txt}."
    )


async def chat(db: AsyncSession, world: World, player: Player, message: str) -> str:
    if len(message) > 2000:
        raise GameError("Pip's attention span caps at 2000 characters")
    today_msgs = await db.scalar(
        select(func.count()).select_from(TutorMessage).where(
            TutorMessage.player_id == player.id,
            TutorMessage.world_day == world.world_day,
            TutorMessage.role == "user",
        )
    )
    db.add(TutorMessage(world_id=world.id, player_id=player.id, role="user",
                        content=message, world_day=world.world_day))
    if today_msgs >= PER_STUDENT_DAILY_MSGS:
        reply = ("Even a pigeon must rest his beak! We've talked plenty today — "
                 "go put some of it into practice and find me tomorrow.")
    else:
        reply = await _llm_reply(db, world, player, message)
    db.add(TutorMessage(world_id=world.id, player_id=player.id, role="tutor",
                        content=reply, world_day=world.world_day))
    await emit(db, world, "tutor_chat", {"chars": len(message)}, actor=player.id)
    player.last_active_day = world.world_day
    return reply


async def _llm_reply(db: AsyncSession, world: World, player: Player, message: str) -> str:
    client = _client()
    if client is None or _budget_remaining(world) <= 0:
        return random.choice(CANNED_REPLIES)
    history = (
        await db.scalars(
            select(TutorMessage)
            .where(TutorMessage.world_id == world.id, TutorMessage.player_id == player.id)
            .order_by(TutorMessage.id.desc()).limit(12)
        )
    ).all()
    context = await _student_context(db, world, player)
    messages = []
    for m in reversed(history):
        messages.append({"role": "user" if m.role == "user" else "assistant",
                         "content": m.content})
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": message})
    messages[-1] = {"role": "user", "content": f"{context}\n\n{message}"}
    try:
        response = await client.messages.create(
            model=get_settings().model_tutor,
            max_tokens=400,
            system=[{"type": "text", "text": PIP_SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        _record_usage(world, response.usage.input_tokens + response.usage.output_tokens)
        return next((b.text for b in response.content if b.type == "text"),
                    random.choice(CANNED_REPLIES))
    except Exception:
        return random.choice(CANNED_REPLIES)


# -- tutor checks -----------------------------------------------------------------

async def next_check(db: AsyncSession, world: World, player: Player) -> dict | None:
    """Pick the next contextual check: gameplay-triggered first, cadence floor
    as fallback; never repeat a correctly-answered question."""
    answered = {
        row[0]
        for row in (
            await db.execute(
                select(CheckAttempt.question_id).where(
                    CheckAttempt.player_id == player.id, CheckAttempt.correct)
            )
        ).all()
    }
    recent_kinds = {
        row[0]
        for row in (
            await db.execute(
                select(EconEvent.kind).where(
                    EconEvent.world_id == world.id,
                    EconEvent.actor_player_id == player.id,
                    EconEvent.world_day >= world.world_day - 2,
                ).distinct()
            )
        ).all()
    }
    tags = set(recent_kinds)
    rules = world.market_rules or {}
    if rules.get("ceilings"):
        tags.add("ceiling")
    if world.current_week == 2:
        tags.add("festival")
    if world.current_week == 6:
        tags.add("fishery")
    pool = [q for q in questions_for_context(world.current_week, tags)
            if q.id not in answered]
    if not pool:
        pool = [q for q in questions_for_week(world.current_week) if q.id not in answered]
    if not pool:
        pool = [q for w in range(1, world.current_week + 1)
                for q in questions_for_week(w) if q.id not in answered]
    if not pool:
        return None
    rng = random.Random(f"{player.id}:{world.world_day}")
    q = rng.choice(pool)
    return {
        "question_id": q.id, "kind": q.kind, "prompt": q.prompt,
        "choices": list(q.choices), "los": [LEARNING_OBJECTIVES[lo].text for lo in q.los],
    }


async def answer_check(db: AsyncSession, world: World, player: Player,
                       question_id: str, answer: str) -> dict:
    q = QUESTIONS.get(question_id)
    if q is None:
        raise GameError("unknown question")
    if q.kind == "mcq":
        try:
            idx = int(answer)
        except ValueError:
            raise GameError("answer an option number") from None
        correct = idx == q.answer
        score = 100 if correct else 0
        feedback = (
            "Precisely so! " + _why(q) if correct
            else f"Not quite — the answer was: \"{q.choices[q.answer]}\". " + _why(q)
        )
    else:
        score, feedback = await _grade_free(world, q, answer)
        correct = score >= 60
    db.add(CheckAttempt(world_id=world.id, player_id=player.id, question_id=q.id,
                        world_day=world.world_day, answer=str(answer)[:2000],
                        correct=correct, score=score, feedback=feedback))
    for lo_id in q.los:
        await _update_mastery(db, world, player, lo_id, score)
    await emit(db, world, "check_answered",
               {"question": q.id, "correct": correct, "score": score}, actor=player.id)
    player.last_active_day = world.world_day
    return {"correct": correct, "score": score, "feedback": feedback}


def _why(q) -> str:
    los = ", ".join(LEARNING_OBJECTIVES[lo].text for lo in q.los)
    return f"(This one is about: {los}.)"


async def _grade_free(world: World, q, answer: str) -> tuple[int, str]:
    client = _client()
    if client is not None and _budget_remaining(world) > 0:
        try:
            response = await client.messages.create(
                model=get_settings().model_tutor,
                max_tokens=200,
                system=[{"type": "text",
                         "text": "You grade one-sentence answers from intro econ students. "
                                 "Reply with exactly: a score 0-100, a pipe, then one warm "
                                 "sentence of feedback in the voice of a tutor pigeon. "
                                 "Example: 85|Sharp thinking — you spotted the shortage.",
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user",
                           "content": f"QUESTION: {q.prompt}\nRUBRIC: {q.rubric}\n"
                                      f"STUDENT ANSWER: {answer[:1500]}"}],
            )
            _record_usage(world, response.usage.input_tokens + response.usage.output_tokens)
            text = next((b.text for b in response.content if b.type == "text"), "")
            score_s, _, feedback = text.partition("|")
            score = max(0, min(100, int(score_s.strip())))
            return score, feedback.strip() or "Noted in my ledger."
        except Exception:
            pass
    # Keyword fallback — degraded but functional.
    low = answer.lower()
    hits = sum(1 for kw in q.keywords if kw in low)
    score = min(100, 40 + hits * 30) if hits else 20
    feedback = ("A solid instinct — I see the key idea in there." if score >= 60 else
                "Hmm — have another look at the rubric idea: " + (q.rubric or "see the text."))
    return score, feedback


async def _update_mastery(db: AsyncSession, world: World, player: Player,
                          lo_id: str, score: int) -> None:
    row = await db.scalar(
        select(MasteryEstimate).where(
            MasteryEstimate.world_id == world.id,
            MasteryEstimate.player_id == player.id,
            MasteryEstimate.lo_id == lo_id,
        )
    )
    if row is None:
        row = MasteryEstimate(world_id=world.id, player_id=player.id, lo_id=lo_id,
                              score=0, attempts=0)
        db.add(row)
        await db.flush()
    # Recency-weighted EMA on a 0-1000 scale; wrong-then-right counts as growth.
    alpha = 0.4
    row.score = round((1 - alpha) * row.score + alpha * score * 10)
    row.attempts += 1


# -- proactive nudges ---------------------------------------------------------------

NUDGE_RULES = [
    ("underpricing", lambda ctx: ctx.get("sold_below_close", 0) >= 3,
     "You've sold below the market close three times today, friend. Walk with me — "
     "what is the order book telling you about what buyers will pay?"),
    ("idle_effort", lambda ctx: ctx.get("effort", 0) >= 35,
     "Your effort bar is brimming and the day is wasting! Scarce resources left "
     "unused are their own little tragedy."),
    ("ceiling_active", lambda ctx: ctx.get("ceiling_goods"),
     "A price decree is in force. Watch what happens to the shelves — and ask "
     "yourself who wins and who loses. There may be a quiz in it for you."),
]


async def get_nudge(db: AsyncSession, world: World, player: Player) -> str | None:
    sold_below = 0
    closes: dict[str, int] = {}
    snaps = (
        await db.scalars(
            select(PriceSnapshot).where(PriceSnapshot.world_id == world.id,
                                        PriceSnapshot.world_day == world.world_day - 1,
                                        PriceSnapshot.close.is_not(None))
        )
    ).all()
    for s in snaps:
        closes[s.good_id] = s.close
    from ..models import DbTrade

    sells = (
        await db.scalars(
            select(DbTrade).where(DbTrade.world_id == world.id,
                                  DbTrade.seller_player_id == player.id,
                                  DbTrade.world_day == world.world_day)
        )
    ).all()
    for t in sells:
        if t.good_id in closes and t.price < closes[t.good_id] * 0.9:
            sold_below += 1
    ctx = {
        "sold_below_close": sold_below,
        "effort": player.effort,
        "ceiling_goods": list(((world.market_rules or {}).get("ceilings") or {}).keys()),
    }
    for _, predicate, text in NUDGE_RULES:
        if predicate(ctx):
            return text
    return None

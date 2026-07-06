from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ..deps import DB, CurrentPlayer, WorldDep
from ..models import MasteryEstimate, TutorMessage
from ..pedagogy import tutor as tutor_svc
from ..pedagogy.bank import LEARNING_OBJECTIVES

router = APIRouter(tags=["tutor"])


class ChatIn(BaseModel):
    message: str


@router.post("/worlds/{world_id}/tutor/chat")
async def chat(body: ChatIn, db: DB, world: WorldDep, player: CurrentPlayer):
    reply = await tutor_svc.chat(db, world, player, body.message)
    return {"reply": reply}


@router.get("/worlds/{world_id}/tutor/history")
async def history(db: DB, world: WorldDep, player: CurrentPlayer, limit: int = 30):
    rows = (
        await db.scalars(
            select(TutorMessage)
            .where(TutorMessage.world_id == world.id,
                   TutorMessage.player_id == player.id)
            .order_by(TutorMessage.id.desc()).limit(min(limit, 100))
        )
    ).all()
    return [{"role": m.role, "content": m.content, "day": m.world_day}
            for m in reversed(rows)]


@router.get("/worlds/{world_id}/tutor/check")
async def next_check(db: DB, world: WorldDep, player: CurrentPlayer,
                     lo: str | None = None):
    check = await tutor_svc.next_check(db, world, player, lo_id=lo)
    return check or {"done": True,
                     "message": "Pip has nothing to quiz you on. Astonishing."}


class AnswerIn(BaseModel):
    question_id: str
    answer: str


@router.post("/worlds/{world_id}/tutor/check")
async def answer_check(body: AnswerIn, db: DB, world: WorldDep, player: CurrentPlayer):
    return await tutor_svc.answer_check(db, world, player, body.question_id, body.answer)


@router.post("/worlds/{world_id}/tutor/check/refine")
async def refine_check(body: AnswerIn, db: DB, world: WorldDep,
                       player: CurrentPlayer):
    """Follow-up on a graded free response: refine the answer or ask a
    clarifying question; Pip re-grades with the whole exchange in view."""
    return await tutor_svc.refine_check(db, world, player,
                                        body.question_id, body.answer)


@router.get("/worlds/{world_id}/tutor/mastery")
async def my_mastery(db: DB, world: WorldDep, player: CurrentPlayer):
    rows = (
        await db.scalars(
            select(MasteryEstimate).where(MasteryEstimate.world_id == world.id,
                                          MasteryEstimate.player_id == player.id)
        )
    ).all()
    by_lo = {m.lo_id: m for m in rows}
    return [
        {"lo_id": lo.id, "text": lo.text, "short": lo.short, "bloom": lo.bloom,
         "week": lo.week,
         "pct": round(by_lo[lo.id].score / 10) if lo.id in by_lo else None,
         "attempts": by_lo[lo.id].attempts if lo.id in by_lo else 0}
        for lo in LEARNING_OBJECTIVES.values() if lo.week <= world.current_week
    ]

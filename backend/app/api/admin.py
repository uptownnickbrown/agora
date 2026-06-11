"""Platform admin: tenancy overview, balance params, system health (spec §3.3)."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from .. import template as T
from ..deps import DB, Admin
from ..models import Course, Player, Section, User, World

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
async def overview(db: DB, admin: Admin):
    worlds = (await db.scalars(select(World))).all()
    out = []
    for w in worlds:
        section = await db.get(Section, w.section_id)
        course = await db.get(Course, section.course_id)
        instructor = await db.get(User, course.instructor_id)
        students = await db.scalar(
            select(func.count(Player.id)).where(Player.world_id == w.id, ~Player.is_npc))
        out.append({
            "world_id": str(w.id), "course": course.title, "section": section.name,
            "instructor": instructor.email, "state": w.state, "week": w.current_week,
            "day": w.world_day, "students": students,
        })
    users = await db.scalar(select(func.count(User.id)))
    return {"worlds": out, "total_users": users, "template": T.TEMPLATE_VERSION}


@router.get("/balance")
async def balance(admin: Admin):
    return {"balance": T.BALANCE,
            "goods": {g.id: {"anchor": g.anchor, "tier": g.tier,
                             "unlock_week": g.unlock_week} for g in T.GOODS.values()},
            "npc_flows": T.NPC_FLOWS, "npc_bands": T.NPC_BANDS}

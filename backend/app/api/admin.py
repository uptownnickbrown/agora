"""Platform admin: tenancy overview, balance params, system health (spec §3.3)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select

from .. import template as T
from ..config import get_settings
from ..deps import DB, Admin
from ..models import Course, Player, Section, User, World

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/demo/rotate")
async def rotate_demo(x_agora_ops_token: str = Header(default="")):
    """Enqueue a demo-world rotation on the worker (blue-green, force).

    Gated by the AGORA_OPS_TOKEN shared secret rather than a user account so
    it can be driven from anywhere HTTPS reaches — no DB credentials, no SSH.
    The api only enqueues; the seed runs on the worker over private
    networking, and a failed seed never touches the live demo."""
    settings = get_settings()
    if not settings.ops_token or not secrets.compare_digest(
            x_agora_ops_token, settings.ops_token):
        raise HTTPException(403, "ops token required")
    from arq import create_pool
    from arq.connections import RedisSettings

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        job = await pool.enqueue_job("demo_reset", force=True)
    finally:
        await pool.close()
    return {"enqueued": job.job_id if job else None}


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

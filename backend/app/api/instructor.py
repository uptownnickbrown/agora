"""Instructor god mode: dashboard, feed, interventions, pacing, gradebook,
playbook, world lifecycle. Everything diegetic faces students; this is the
backstage door.
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import select

from .. import template as T
from ..deps import DB, CurrentUser, Instructor, WorldDep
from ..models import (
    DetectedMoment,
    Intervention,
    Player,
    PriceSnapshot,
    ScheduledEvent,
    World,
    WorldDayStat,
)
from ..pedagogy.grades import gradebook, gradebook_csv, mastery_heatmap
from ..pedagogy.playbook import build_playbook
from ..services import interventions as int_svc
from ..services import worlds as worlds_svc
from ..services.close import run_daily_close
from ..services.npc import refresh_npc_orders

router = APIRouter(prefix="", tags=["instructor"])


class CreateWorldIn(BaseModel):
    course_title: str
    section_name: str
    expected_students: int = 30
    pacing: str = "manual"  # manual | calendar


@router.post("/instructor/worlds")
async def create_world(body: CreateWorldIn, db: DB, user: CurrentUser):
    world = await worlds_svc.create_world(
        db, user, body.course_title, body.section_name,
        {"expected_students": body.expected_students, "pacing": body.pacing},
    )
    user.is_instructor = True
    await refresh_npc_orders(db, world)  # markets alive before the first student
    return {"world_id": str(world.id), "join_code": world.join_code}


@router.get("/worlds/{world_id}/instructor/dashboard")
async def dashboard(db: DB, world: WorldDep, instructor: Instructor):
    players = (
        await db.scalars(select(Player).where(Player.world_id == world.id, ~Player.is_npc))
    ).all()
    day_stats = (
        await db.scalars(
            select(WorldDayStat).where(WorldDayStat.world_id == world.id)
            .order_by(WorldDayStat.world_day)
        )
    ).all()
    snaps = (
        await db.scalars(
            select(PriceSnapshot).where(PriceSnapshot.world_id == world.id)
            .order_by(PriceSnapshot.world_day)
        )
    ).all()
    charts: dict[str, list] = {}
    for s in snaps:
        charts.setdefault(s.good_id, []).append(
            {"day": s.world_day, "close": s.close, "volume": s.volume,
             "unfilled": s.unfilled_demand})
    return {
        "world": {"id": str(world.id), "week": world.current_week, "day": world.world_day,
                  "state": world.state, "join_code": world.join_code,
                  "market_rules": world.market_rules, "smog": world.smog,
                  "fish_stock": world.fish_stock,
                  "pacing": (world.config or {}).get("pacing")},
        "roster": [{"merchant": p.merchant_name, "coins": p.coins,
                    "last_active_day": p.last_active_day,
                    "player_id": str(p.id)} for p in players],
        "vitals": [{"day": d.world_day, "gini_bp": d.gini_bp, "volume": d.total_volume,
                    "active": d.active_players, "smog": d.smog,
                    "fish_stock": d.fish_stock} for d in day_stats],
        "charts": charts,
    }


@router.get("/worlds/{world_id}/instructor/feed")
async def feed(db: DB, world: WorldDep, instructor: Instructor, limit: int = 50):
    moments = (
        await db.scalars(
            select(DetectedMoment).where(DetectedMoment.world_id == world.id)
            .order_by(DetectedMoment.created_at.desc()).limit(min(limit, 200))
        )
    ).all()
    history = (
        await db.scalars(
            select(Intervention).where(Intervention.world_id == world.id)
            .order_by(Intervention.created_at.desc()).limit(20)
        )
    ).all()
    return {
        "moments": [{"id": str(m.id), "day": m.world_day, "kind": m.kind,
                     "severity": m.severity, "summary": m.summary,
                     "payload": m.payload} for m in moments],
        "interventions": [{"day": i.world_day, "kind": i.kind, "params": i.params,
                           "crier": i.crier_copy} for i in history],
    }


@router.get("/worlds/{world_id}/instructor/interventions")
async def catalog(world: WorldDep, instructor: Instructor):
    return int_svc.CATALOG


class InterventionIn(BaseModel):
    kind: str
    params: dict = {}
    schedule_day: int | None = None
    headline: str | None = None


@router.post("/worlds/{world_id}/instructor/interventions/preview")
async def preview(body: InterventionIn, world: WorldDep, instructor: Instructor):
    return {"preview": await int_svc.preview(body.kind, body.params)}


@router.post("/worlds/{world_id}/instructor/interventions")
async def execute(body: InterventionIn, db: DB, world: WorldDep, instructor: Instructor):
    if body.schedule_day is not None:
        await int_svc.schedule(db, world, body.kind, body.params, body.schedule_day)
        return {"scheduled": True, "day": body.schedule_day}
    return await int_svc.execute(db, world, body.kind, body.params, body.headline)


@router.post("/worlds/{world_id}/instructor/advance-week")
async def advance(db: DB, world: WorldDep, instructor: Instructor):
    await worlds_svc.advance_week(db, world)
    return {"week": world.current_week}


class StateIn(BaseModel):
    state: str


@router.post("/worlds/{world_id}/instructor/state")
async def set_state(body: StateIn, db: DB, world: WorldDep, instructor: Instructor):
    await worlds_svc.set_state(db, world, body.state)
    return {"state": world.state}


@router.post("/worlds/{world_id}/instructor/close-day")
async def close_day(db: DB, world: WorldDep, instructor: Instructor):
    """Manual daily close (the worker runs this on schedule in production)."""
    report = await run_daily_close(db, world)
    return report


@router.get("/worlds/{world_id}/instructor/gradebook")
async def grades(db: DB, world: WorldDep, instructor: Instructor):
    return await gradebook(db, world)


@router.get("/worlds/{world_id}/instructor/gradebook.csv")
async def grades_csv(db: DB, world: WorldDep, instructor: Instructor):
    csv_text = await gradebook_csv(db, world)
    return Response(content=csv_text, media_type="text/csv")


@router.get("/worlds/{world_id}/instructor/heatmap")
async def heatmap(db: DB, world: WorldDep, instructor: Instructor):
    return await mastery_heatmap(db, world)


@router.get("/worlds/{world_id}/instructor/playbook")
async def playbook(db: DB, world: WorldDep, instructor: Instructor,
                   week: int | None = None):
    return await build_playbook(db, world, week)


class GradeWeightsIn(BaseModel):
    participation: float = 0.5
    mastery: float = 0.5


@router.post("/worlds/{world_id}/instructor/grade-weights")
async def grade_weights(body: GradeWeightsIn, db: DB, world: WorldDep,
                        instructor: Instructor):
    config = dict(world.config or {})
    config["grade_weights"] = {"participation": body.participation,
                               "mastery": body.mastery}
    world.config = config
    return config["grade_weights"]

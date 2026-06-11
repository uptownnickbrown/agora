"""Self-serve demo entry: one click from the landing page into a live world.

POST /demo/student    -> a fresh visitor merchant in the demo world + tour flag
POST /demo/instructor -> the demo world's instructor (god mode, shared)

Enabled in dev, or when AGORA_DEMO_ENABLED=true. The demo world is whichever
world has config.is_demo, preferring the furthest-along one.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..config import get_settings
from ..deps import DB
from ..models import World
from ..services import auth as auth_svc
from ..services import worlds as worlds_svc

router = APIRouter(prefix="/demo", tags=["demo"])


def _guard():
    s = get_settings()
    if s.env not in ("dev", "test") and not s.demo_enabled:
        raise HTTPException(403, "the demo is not enabled on this server")


async def _demo_world(db) -> World:
    worlds = (await db.scalars(select(World))).all()
    demos = [w for w in worlds
             if (w.config or {}).get("is_demo")
             and w.state not in ("epilogue", "archived")]
    if not demos:
        raise HTTPException(404, "no demo world is seeded (or it has ended) — "
                                 "run scripts/reset_demo.py")
    # Newest seed wins: reset_demo.py rotates worlds rather than mutating them.
    return max(demos, key=lambda w: (w.created_at, w.world_day))


@router.post("/student")
async def demo_student(db: DB):
    _guard()
    world = await _demo_world(db)
    # Two visitors clicking at the same instant get distinct merchants; on an
    # astronomically unlucky handle collision we just roll again.
    for _ in range(3):
        handle = secrets.token_hex(4)
        try:
            user = await auth_svc.register(
                db, f"visitor.{handle}@agora-demo.org",
                f"Visitor {handle[:4].upper()}")
            break
        except Exception:
            continue
    else:
        raise HTTPException(500, "could not mint a visitor — try again")
    player = await worlds_svc.join_world(db, user, world.join_code)
    session = await auth_svc._create_session(db, user)
    return {"token": session.token, "world_id": str(world.id),
            "merchant": player.merchant_name, "role": "student"}


@router.post("/instructor")
async def demo_instructor(db: DB):
    _guard()
    world = await _demo_world(db)
    instructor_id = await worlds_svc.instructor_for_world(db, world)
    from ..models import User

    user = await db.get(User, instructor_id)
    session = await auth_svc._create_session(db, user)
    return {"token": session.token, "world_id": str(world.id), "role": "instructor"}

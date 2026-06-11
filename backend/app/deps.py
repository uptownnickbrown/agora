"""FastAPI dependencies: DB session, auth, role guards, world scoping."""
from __future__ import annotations

import contextvars
import uuid
from typing import Annotated, AsyncIterator

from fastapi import Depends, Header, HTTPException, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import make_engine, make_session_factory
from .models import Player, User, World
from .services.auth import resolve_session
from .services.worlds import instructor_for_world

_session_factory: async_sessionmaker | None = None

# The request's session, for CommitBeforeResponse (main.py). Dependency
# teardown can run AFTER the response is sent, so committing there leaves a
# window where a client's immediate follow-up request reads stale state —
# the middleware commits before the first response byte instead.
current_db_session: contextvars.ContextVar[AsyncSession | None] = \
    contextvars.ContextVar("current_db_session", default=None)


def set_session_factory(factory: async_sessionmaker) -> None:
    global _session_factory
    _session_factory = factory


async def get_db() -> AsyncIterator[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory(make_engine())
    async with _session_factory() as session:
        token = current_db_session.set(session)
        try:
            yield session
            await session.commit()  # safety net; middleware usually beat us
        except Exception:
            await session.rollback()
            raise
        finally:
            current_db_session.reset(token)


DB = Annotated[AsyncSession, Depends(get_db)]


async def current_user(db: DB, authorization: str = Header(default="")) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    user = await resolve_session(db, authorization.removeprefix("Bearer "))
    if user is None:
        raise HTTPException(401, "invalid or expired session")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def world_from_path(db: DB, world_id: uuid.UUID = Path()) -> World:
    world = await db.get(World, world_id)
    if world is None:
        raise HTTPException(404, "world not found")
    return world


WorldDep = Annotated[World, Depends(world_from_path)]


async def current_player(request: Request, db: DB, world: WorldDep,
                         user: CurrentUser) -> Player:
    from sqlalchemy import select

    q = select(Player).where(Player.world_id == world.id,
                             Player.user_id == user.id)
    # Mutating requests lock the player row: coins, effort and inventory all
    # hang off it, and two simultaneous actions (double-click, two tabs) must
    # serialize rather than double-spend. Reads stay lock-free.
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        q = q.with_for_update()
    player = await db.scalar(q)
    if player is None:
        raise HTTPException(403, "you are not enrolled in this world")
    return player


CurrentPlayer = Annotated[Player, Depends(current_player)]


async def require_instructor(db: DB, world: WorldDep, user: CurrentUser) -> User:
    if user.is_platform_admin:
        return user
    if await instructor_for_world(db, world) != user.id:
        raise HTTPException(403, "instructor access required")
    return user


Instructor = Annotated[User, Depends(require_instructor)]


async def require_admin(user: CurrentUser) -> User:
    if not user.is_platform_admin:
        raise HTTPException(403, "platform admin required")
    return user


Admin = Annotated[User, Depends(require_admin)]

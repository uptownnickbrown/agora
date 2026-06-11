"""Live market feed: trades, crier headlines, day-close pings."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ..bus import bus
from ..deps import get_db
from ..models import Player
from ..services.auth import resolve_session

router = APIRouter()


@router.websocket("/worlds/{world_id}/ws")
async def world_feed(websocket: WebSocket, world_id: uuid.UUID):
    token = websocket.query_params.get("token", "")
    authorized = False
    async for db in get_db():
        user = await resolve_session(db, token)
        if user is not None:
            player = await db.scalar(
                select(Player).where(Player.world_id == world_id,
                                     Player.user_id == user.id)
            )
            authorized = player is not None or user.is_instructor or user.is_platform_admin
    if not authorized:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = bus.subscribe(str(world_id))
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        bus.unsubscribe(str(world_id), queue)

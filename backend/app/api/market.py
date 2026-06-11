from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..deps import DB, CurrentPlayer, WorldDep
from ..services import market as market_svc

router = APIRouter(tags=["market"])


class OrderIn(BaseModel):
    good_id: str
    side: str
    qty: int = Field(gt=0, le=10_000)
    price: int | None = Field(default=None, gt=0, le=1_000_000)
    ttl_days: int = Field(default=1, ge=1, le=2)


@router.post("/worlds/{world_id}/orders")
async def place_order(body: OrderIn, db: DB, world: WorldDep, player: CurrentPlayer):
    result = await market_svc.place_order(
        db, world, player, body.good_id, body.side, body.qty, body.price, body.ttl_days
    )
    return result


@router.delete("/worlds/{world_id}/orders/{order_id}")
async def cancel_order(order_id: uuid.UUID, db: DB, world: WorldDep, player: CurrentPlayer):
    await market_svc.cancel_order(db, world, player, order_id)
    return {"cancelled": True}


@router.get("/worlds/{world_id}/markets/{good_id}/book")
async def book(good_id: str, db: DB, world: WorldDep, player: CurrentPlayer):
    return await market_svc.book_snapshot(db, world, good_id)


@router.get("/worlds/{world_id}/markets/{good_id}/history")
async def history(good_id: str, db: DB, world: WorldDep, player: CurrentPlayer):
    return await market_svc.price_history(db, world, good_id)


@router.get("/worlds/{world_id}/markets/{good_id}/tape")
async def tape(good_id: str, db: DB, world: WorldDep, player: CurrentPlayer):
    return await market_svc.trade_tape(db, world, good_id)

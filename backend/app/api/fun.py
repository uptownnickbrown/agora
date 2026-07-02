from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..deps import DB, CurrentPlayer, WorldDep
from ..services import fun as fun_svc

router = APIRouter(tags=["fun"])


@router.get("/worlds/{world_id}/puzzle")
async def puzzle(db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.get_puzzle_state(db, world, player)


class GuessIn(BaseModel):
    terms: list[str] = Field(min_length=4, max_length=4)


@router.post("/worlds/{world_id}/puzzle/guess")
async def guess(body: GuessIn, db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.guess_puzzle(db, world, player, body.terms)


@router.post("/worlds/{world_id}/fishing/cast")
async def cast(db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.cast_line(db, world, player)


@router.get("/worlds/{world_id}/merchant")
async def merchant(db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.merchant_state(db, world, player)


class MerchantIn(BaseModel):
    legs: list[dict]


@router.post("/worlds/{world_id}/merchant/submit")
async def merchant_submit(body: MerchantIn, db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.merchant_submit(db, world, player, body.legs)


@router.get("/worlds/{world_id}/haggle")
async def haggle(db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.haggle_state(db, world, player)


class OfferIn(BaseModel):
    price: int = Field(gt=0, le=100_000)


@router.post("/worlds/{world_id}/haggle/offer")
async def haggle_offer(body: OfferIn, db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.haggle_offer(db, world, player, body.price)


@router.post("/worlds/{world_id}/haggle/walk")
async def haggle_walk(db: DB, world: WorldDep, player: CurrentPlayer):
    return await fun_svc.haggle_walk(db, world, player)


@router.get("/worlds/{world_id}/boutique")
async def boutique(db: DB, world: WorldDep, player: CurrentPlayer):
    return fun_svc.COSMETICS["boutique"]


class BuyIn(BaseModel):
    cosmetic_id: str


@router.post("/worlds/{world_id}/boutique/buy")
async def buy(body: BuyIn, db: DB, world: WorldDep, player: CurrentPlayer):
    await fun_svc.buy_cosmetic(db, world, player, body.cosmetic_id)
    return {"bought": body.cosmetic_id, "coins": player.coins}

"""Student-facing routes: world state, inventory, actions, shop, facilities,
fun layer, tutor. All world-scoped under /worlds/{world_id}/...
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import template as T
from ..deps import DB, CurrentPlayer, CurrentUser, WorldDep
from ..models import (
    CrierPost,
    DbOrder,
    EconEvent,
    Facility,
    GuildLoan,
    Inventory,
    License,
    PlayerAchievement,
    PlayerCosmetic,
    ShopListing,
)
from ..pedagogy import recap as recap_svc
from ..pedagogy import tutor as tutor_svc
from ..services import compacts as compacts_svc
from ..services import fun as fun_svc
from ..services import licenses as lic_svc
from ..services import production as prod_svc
from ..services import shops as shops_svc
from ..services import stats as stats_svc
from ..services import worlds as worlds_svc
from ..services.common import GameError, adjust_coins

router = APIRouter(tags=["student"])


class JoinIn(BaseModel):
    join_code: str


@router.post("/join")
async def join(body: JoinIn, db: DB, user: CurrentUser):
    player = await worlds_svc.join_world(db, user, body.join_code)
    return {"world_id": str(player.world_id), "player_id": str(player.id),
            "merchant": player.merchant_name, "aptitude": player.aptitude_good}


@router.get("/worlds/{world_id}/state")
async def world_state(db: DB, world: WorldDep, player: CurrentPlayer):
    await fun_svc.login_streak(db, world, player)
    invs = (
        await db.scalars(
            select(Inventory).where(Inventory.world_id == world.id,
                                    Inventory.player_id == player.id, Inventory.qty > 0)
        )
    ).all()
    facilities = (
        await db.scalars(
            select(Facility).where(Facility.world_id == world.id,
                                   Facility.player_id == player.id)
        )
    ).all()
    orders = (
        await db.scalars(
            select(DbOrder).where(DbOrder.world_id == world.id,
                                  DbOrder.player_id == player.id,
                                  DbOrder.status == "open")
        )
    ).all()
    achievements = (
        await db.scalars(
            select(PlayerAchievement).where(PlayerAchievement.player_id == player.id)
        )
    ).all()
    cosmetics = (
        await db.scalars(
            select(PlayerCosmetic).where(PlayerCosmetic.player_id == player.id)
        )
    ).all()
    loan = await db.scalar(
        select(GuildLoan).where(GuildLoan.world_id == world.id,
                                GuildLoan.player_id == player.id,
                                GuildLoan.outstanding > 0)
    )
    nudge = await tutor_svc.get_nudge(db, world, player)
    licenses = (
        await db.scalars(
            select(License).where(License.world_id == world.id,
                                  License.player_id == player.id,
                                  ~License.revoked)
        )
    ).all()
    check = await tutor_svc.next_check(db, world, player)
    goods = [
        {"id": g.id, "name": g.name, "tier": g.tier,
         "gatherable": g.gatherable, "license_required": g.license_required,
         "aptitude": g.id == player.aptitude_good}
        for g in T.GOODS.values() if g.unlock_week <= world.current_week
    ]
    return {
        "world": {"id": str(world.id), "week": world.current_week,
                  "day": world.world_day, "state": world.state,
                  "market_rules": world.market_rules,
                  "fishing_rules": world.fishing_rules,
                  "smog": world.smog if world.current_week >= 6 else None,
                  "demo": bool((world.config or {}).get("is_demo"))},
        "player": {"id": str(player.id), "merchant": player.merchant_name,
                   "coins": player.coins, "effort": player.effort,
                   "aptitude": player.aptitude_good},
        "goods": goods,
        "inventory": {i.good_id: i.qty for i in invs},
        "facilities": [{"id": str(f.id), "kind": f.kind, "tier": f.tier,
                        "workers": f.workers, "scrubber": f.scrubber,
                        "name": T.FACILITIES[f.kind].name,
                        "output": T.FACILITIES[f.kind].output} for f in facilities],
        "open_orders": [{"id": str(o.id), "good_id": o.good_id, "side": o.side,
                         "qty": o.qty, "remaining": o.remaining, "price": o.price,
                         "expires_day": o.expires_day} for o in orders],
        "achievements": [a.achievement_id for a in achievements],
        "cosmetics": [c.cosmetic_id for c in cosmetics],
        "loan": {"outstanding": loan.outstanding} if loan else None,
        "nudge": nudge,
        "licenses": sorted({l.good_id for l in licenses}),
        "check_available": check is not None,
    }


# -- actions ---------------------------------------------------------------------

class GatherIn(BaseModel):
    good_id: str
    effort: int = Field(gt=0, le=40)


@router.post("/worlds/{world_id}/gather")
async def gather(body: GatherIn, db: DB, world: WorldDep, player: CurrentPlayer):
    qty = await prod_svc.gather(db, world, player, body.good_id, body.effort)
    return {"gathered": qty, "good_id": body.good_id, "effort_left": player.effort}


class CraftIn(BaseModel):
    output: str
    runs: int = Field(default=1, gt=0, le=100)


@router.post("/worlds/{world_id}/craft")
async def craft(body: CraftIn, db: DB, world: WorldDep, player: CurrentPlayer):
    qty = await prod_svc.craft(db, world, player, body.output, body.runs)
    return {"crafted": qty, "good_id": body.output, "effort_left": player.effort}


class BuildIn(BaseModel):
    kind: str


@router.post("/worlds/{world_id}/facilities")
async def build(body: BuildIn, db: DB, world: WorldDep, player: CurrentPlayer):
    fac = await prod_svc.build_facility(db, world, player, body.kind)
    return {"facility_id": str(fac.id), "kind": fac.kind, "tier": fac.tier}


@router.post("/worlds/{world_id}/facilities/{facility_id}/upgrade")
async def upgrade(facility_id: uuid.UUID, db: DB, world: WorldDep, player: CurrentPlayer):
    fac = await prod_svc.upgrade_facility(db, world, player, facility_id)
    return {"facility_id": str(fac.id), "tier": fac.tier}


class HireIn(BaseModel):
    workers: int = Field(ge=0, le=12)


@router.post("/worlds/{world_id}/facilities/{facility_id}/workers")
async def hire(facility_id: uuid.UUID, body: HireIn, db: DB, world: WorldDep,
               player: CurrentPlayer):
    fac = await prod_svc.hire_workers(db, world, player, facility_id, body.workers)
    return {"facility_id": str(fac.id), "workers": fac.workers}


@router.post("/worlds/{world_id}/facilities/{facility_id}/scrubber")
async def scrubber(facility_id: uuid.UUID, db: DB, world: WorldDep, player: CurrentPlayer):
    fac = await prod_svc.buy_scrubber(db, world, player, facility_id)
    return {"facility_id": str(fac.id), "scrubber": True}


# -- shop --------------------------------------------------------------------------

class ListingIn(BaseModel):
    good_id: str
    price: int = Field(gt=0)
    qty: int = Field(ge=0)


@router.post("/worlds/{world_id}/shop")
async def set_listing(body: ListingIn, db: DB, world: WorldDep, player: CurrentPlayer):
    listing = await shops_svc.set_listing(db, world, player, body.good_id,
                                          body.price, body.qty)
    return {"good_id": listing.good_id, "price": listing.price, "qty": listing.qty,
            "sold_total": listing.sold_total}


@router.get("/worlds/{world_id}/shop")
async def my_shop(db: DB, world: WorldDep, player: CurrentPlayer):
    listings = (
        await db.scalars(
            select(ShopListing).where(ShopListing.world_id == world.id,
                                      ShopListing.player_id == player.id)
        )
    ).all()
    # Last night's till, from the event log — the player's own demand curve.
    sales = (
        await db.scalars(
            select(EconEvent.payload).where(
                EconEvent.world_id == world.id,
                EconEvent.actor_player_id == player.id,
                EconEvent.kind == "shop_sale",
                EconEvent.world_day == world.world_day - 1)
        )
    ).all()
    ysold: dict[str, int] = {}
    for pl in sales:
        ysold[pl["good"]] = ysold.get(pl["good"], 0) + pl["qty"]
    return [{"good_id": l.good_id, "price": l.price, "qty": l.qty,
             "sold_total": l.sold_total,
             "sold_yesterday": ysold.get(l.good_id, 0)} for l in listings]


# -- guild loan (anti-ruin) -----------------------------------------------------------

@router.post("/worlds/{world_id}/fresh-start")
async def fresh_start(db: DB, world: WorldDep, player: CurrentPlayer):
    if player.coins >= 30:
        raise GameError("the Guild only lends to the truly broke (under 30 coppers)")
    existing = await db.scalar(
        select(GuildLoan).where(GuildLoan.world_id == world.id,
                                GuildLoan.player_id == player.id,
                                GuildLoan.outstanding > 0)
    )
    if existing:
        raise GameError("you already carry a Guild loan")
    amount = T.BALANCE["fresh_start_coins"]
    db.add(GuildLoan(world_id=world.id, player_id=player.id, principal=amount,
                     outstanding=amount, rate_bp_per_day=T.BALANCE["fresh_start_rate_bp"]))
    adjust_coins(player, amount)
    player.bankrupt_resets += 1
    return {"granted": amount, "message": "The Guild believes in second acts. "
                                          "Interest is gentle but real — mind it."}


# -- crier, leaderboards, compacts, licenses, recap ------------------------------------

@router.get("/worlds/{world_id}/crier")
async def crier(db: DB, world: WorldDep, player: CurrentPlayer, limit: int = 20):
    posts = (
        await db.scalars(
            select(CrierPost).where(CrierPost.world_id == world.id)
            .order_by(CrierPost.world_day.desc(), CrierPost.created_at.desc())
            .limit(min(limit, 50))
        )
    ).all()
    return [{"day": p.world_day, "kind": p.kind, "title": p.title, "body": p.body}
            for p in posts]


@router.get("/worlds/{world_id}/leaderboards")
async def leaderboards(db: DB, world: WorldDep, player: CurrentPlayer):
    return await stats_svc.leaderboards(db, world)


@router.get("/worlds/{world_id}/compacts")
async def list_compacts(db: DB, world: WorldDep, player: CurrentPlayer):
    return await compacts_svc.list_compacts(db, world)


class CompactIn(BaseModel):
    name: str
    kind: str
    terms: dict = {}


@router.post("/worlds/{world_id}/compacts")
async def create_compact(body: CompactIn, db: DB, world: WorldDep, player: CurrentPlayer):
    compact = await compacts_svc.create_compact(db, world, player, body.name,
                                                body.kind, body.terms)
    return {"compact_id": str(compact.id)}


@router.post("/worlds/{world_id}/compacts/{compact_id}/join")
async def join_compact(compact_id: uuid.UUID, db: DB, world: WorldDep,
                       player: CurrentPlayer):
    await compacts_svc.join_compact(db, world, player, compact_id)
    return {"joined": True}


@router.post("/worlds/{world_id}/compacts/{compact_id}/leave")
async def leave_compact(compact_id: uuid.UUID, db: DB, world: WorldDep,
                        player: CurrentPlayer):
    await compacts_svc.leave_compact(db, world, player, compact_id)
    return {"left": True}


class BidIn(BaseModel):
    auction_id: str
    amount: int = Field(gt=0)


@router.post("/worlds/{world_id}/license-bids")
async def bid_license(body: BidIn, db: DB, world: WorldDep, player: CurrentPlayer):
    await lic_svc.submit_bid(db, world, player, body.auction_id, body.amount)
    return {"bid": body.amount, "auction": body.auction_id,
            "note": "Sealed. Not even Pip knows the other bids."}


@router.get("/worlds/{world_id}/license-auctions")
async def open_auctions(db: DB, world: WorldDep, player: CurrentPlayer):
    """Open sealed-bid auctions (the Crier announces them; this lists them)."""
    from ..models import LicenseBid, ScheduledEvent

    events = (
        await db.scalars(
            select(ScheduledEvent).where(
                ScheduledEvent.world_id == world.id,
                ScheduledEvent.kind == "license_auction_close",
                ~ScheduledEvent.executed,
            )
        )
    ).all()
    out = []
    for e in events:
        my_bid = await db.scalar(
            select(LicenseBid.amount).where(
                LicenseBid.world_id == world.id,
                LicenseBid.auction_id == e.params.get("auction_id", ""),
                LicenseBid.player_id == player.id,
            )
        )
        out.append({"auction_id": e.params.get("auction_id"),
                    "good": e.params.get("good"),
                    "licenses": e.params.get("licenses"),
                    "closes_day": e.world_day, "my_bid": my_bid})
    return out


@router.get("/worlds/{world_id}/recap")
async def my_recap(db: DB, world: WorldDep, player: CurrentPlayer):
    if world.state not in ("epilogue", "archived") and world.current_week < 7:
        raise HTTPException(403, "recaps unlock in the epilogue")
    return await recap_svc.your_economic_story(db, world, player)

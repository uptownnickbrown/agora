"""Furnish a freshly minted demo visitor with a lived-in mid-course state.

A visitor who lands in the demo world at week 4 should look like someone who
has been playing since week 1: a working shop with last night's till, a couple
of facilities humming, a mastery profile with strengths and one wobble, a
puzzle streak worth protecting. Each visitor gets their OWN copy of this state
(minted per click), so there is no shared-account concurrency to worry about —
two visitors can never clobber each other's shop.

Everything here writes through the same tables the real services use; nothing
is minted off-ledger that the daily close would choke on.
"""
from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from .. import template as T
from ..models import (
    EconEvent,
    Facility,
    MasteryEstimate,
    Player,
    ShopListing,
    Streak,
    World,
)
from ..pedagogy.bank import LEARNING_OBJECTIVES
from .common import get_inventory
from .fun import award

# aptitude -> (raw producer facility, one processing facility downstream)
FACILITY_PLAN = {
    "grain": ("farm", "mill"),
    "wool": ("pasture", "loom"),
    "wood": ("woodlot", "bakery"),
}
# aptitude -> the crafted good their shop is known for
CRAFTED_GOOD = {"grain": "flour", "wool": "cloth", "wood": "bread"}


def _mastery_profile(rng: random.Random, week: int) -> dict[str, float]:
    """Percent mastery per LO: old weeks strong, last week developing, the
    current week mostly unassessed, and always exactly one honest wobble
    (the 'practice a weak objective' demo story needs a red bar)."""
    profile: dict[str, float] = {}
    for lo in LEARNING_OBJECTIVES.values():
        if lo.week > week:
            continue
        age = week - lo.week
        if age >= 2:
            if rng.random() > 0.92:
                continue  # a rare old blank keeps "not yet assessed" honest
            pct = rng.gauss(78, 10)
        elif age == 1:
            if rng.random() > 0.85:
                continue
            pct = rng.gauss(64, 14)
        else:
            if rng.random() > 0.35:
                continue  # this week's objectives are mostly still ahead
            pct = rng.gauss(52, 12)
        # Floor keeps non-wobble cells out of the red, with jitter so a run
        # of clamped rolls doesn't read as a suspicious row of identical 42s.
        profile[lo.id] = max(42.0 + rng.uniform(0, 9), min(96.0, pct))
    if profile:
        wobble = rng.choice(sorted(profile))
        profile[wobble] = rng.uniform(26, 38)
    return profile


async def furnish_visitor(db: AsyncSession, world: World, player: Player) -> None:
    rng = random.Random(str(player.id))
    aptitude = player.aptitude_good or "wool"
    crafted = CRAFTED_GOOD.get(aptitude, "cloth")

    # -- purse and pantry: a mid-course merchant, not a day-one one ----------
    player.coins = 380 + rng.randrange(0, 240)
    player.last_active_day = world.world_day
    for good_id, qty in {
        aptitude: 14 + rng.randrange(0, 10),
        crafted: 4 + rng.randrange(0, 5),
        "bread": 3 + rng.randrange(0, 4),
        "fish": 2 + rng.randrange(0, 3),
    }.items():
        inv = await get_inventory(db, world.id, player.id, good_id)
        inv.qty += qty

    # -- facilities: fixed costs already sunk, working every night -----------
    producer, processor = FACILITY_PLAN.get(aptitude, ("pasture", "loom"))
    db.add(Facility(world_id=world.id, player_id=player.id, kind=producer,
                    tier=2, workers=2))
    db.add(Facility(world_id=world.id, player_id=player.id, kind=processor,
                    tier=1))

    # -- the shop: stocked shelves, real sales history, last night's till ----
    anchor = {g.id: g.anchor for g in T.GOODS.values()}
    shelf = [
        (crafted, int(anchor.get(crafted, 40) * 1.1), 5 + rng.randrange(0, 4),
         18 + rng.randrange(0, 18)),
        (aptitude, anchor.get(aptitude, 20), 7 + rng.randrange(0, 4),
         26 + rng.randrange(0, 22)),
    ]
    for good_id, price, qty, sold_total in shelf:
        db.add(ShopListing(world_id=world.id, player_id=player.id,
                           good_id=good_id, price=price, qty=qty,
                           sold_total=sold_total))
        # Yesterday's passersby, so "sold last night" and the till banner are
        # live from the first pageview.
        db.add(EconEvent(world_id=world.id, world_day=world.world_day - 1,
                         kind="shop_sale", actor_player_id=player.id,
                         payload={"good": good_id, "qty": 2 + rng.randrange(0, 3),
                                  "price": price}))

    # -- streaks worth protecting and a little swagger ------------------------
    db.add(Streak(world_id=world.id, player_id=player.id, kind="puzzle",
                  count=4, best=6, last_day=world.world_day - 1))
    db.add(Streak(world_id=world.id, player_id=player.id, kind="login",
                  count=5, best=7, last_day=world.world_day - 1))
    for achievement in ("traveling_merchant", "first_trade", "silver_tongue"):
        await award(db, world, player, achievement)

    # -- mastery: what six weeks of tutor checks would have left behind ------
    for lo_id, pct in _mastery_profile(rng, world.current_week).items():
        db.add(MasteryEstimate(world_id=world.id, player_id=player.id,
                               lo_id=lo_id, score=round(pct * 10),
                               attempts=2 + rng.randrange(0, 4)))

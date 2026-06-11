"""Phase-0 gate: the spec's promised economic phenomena must emerge in the
headless harness before any UI is built (spec §14 item 15, DECISIONS.md #15).

Each test runs across several seeds — a phenomenon that only appears under one
RNG seed is a coincidence, not an economy.
"""
import statistics

import pytest

from sim.scenarios import (
    CEILING_DAY,
    DROUGHT_DAY,
    FESTIVAL_END,
    FESTIVAL_START,
    bread_ceiling,
    convergence,
    festival_rush,
)

SEEDS = [7, 13, 42]


def closes_between(world, good, first_day, last_day):
    return [
        s.close
        for s in world.stats_for(good)
        if first_day <= s.day <= last_day and s.close is not None
    ]


@pytest.mark.parametrize("seed", SEEDS)
def test_cda_converges_to_competitive_equilibrium(seed):
    """Supply (costs 40..80) and demand (values 60..120) cross at p* = 72."""
    scenario = convergence(seed=seed)
    world = scenario.run()
    settled = closes_between(world, "grain", 5, 15)
    assert settled, "market never traded"
    assert abs(statistics.mean(settled) - 72) <= 10


@pytest.mark.parametrize("seed", SEEDS)
def test_festival_rush_spike_then_glut(seed):
    """Announced demand shock -> shortage & price spike -> supply response ->
    post-festival glut. The Week 2 story arc."""
    scenario = festival_rush(seed=seed)
    world = scenario.run()

    baseline = statistics.mean(closes_between(world, "garments", 4, FESTIVAL_START - 1))
    festival_window = closes_between(world, "garments", FESTIVAL_START, FESTIVAL_END + 1)
    peak = max(festival_window)
    post = closes_between(world, "garments", FESTIVAL_END + 2, 17)

    # Spike: festival prices clear meaningfully above the pre-festival market.
    assert peak >= baseline * 1.4, f"no festival spike: peak {peak} vs baseline {baseline:.0f}"

    # Shortage during the rush: demand goes unfilled at the peak.
    rush_unfilled = max(
        s.unfilled_demand
        for s in world.stats_for("garments")
        if FESTIVAL_START <= s.day <= FESTIVAL_END + 1
    )
    assert rush_unfilled > 0

    # Glut: after the festival the market trades again and prices come back down.
    assert post, "post-festival market never recovered"
    assert min(post) <= peak * 0.6, f"no glut: post min {min(post)} vs peak {peak}"
    post_volume = sum(
        s.volume for s in world.stats_for("garments") if s.day >= FESTIVAL_END + 3
    )
    assert post_volume > 0


@pytest.mark.parametrize("seed", SEEDS)
def test_bread_ceiling_empties_the_shelves(seed):
    """Drought -> price pressure -> ceiling at the old price -> legal trade dries
    up, demand goes unfilled, sellers visibly withdraw. The Week 3 story arc."""
    scenario = bread_ceiling(seed=seed)
    world = scenario.run()
    ceiling = scenario.notes["ceiling_price"]

    pre_stats = [s for s in world.stats_for("bread") if s.day < DROUGHT_DAY]
    post_stats = [s for s in world.stats_for("bread") if s.day > CEILING_DAY]

    # The law holds: nothing trades above the ceiling once imposed.
    assert all(s.high is None or s.high <= ceiling for s in post_stats)

    # Shelves empty: legal volume collapses...
    pre_volume = statistics.mean(s.volume for s in pre_stats[3:])
    post_volume = statistics.mean(s.volume for s in post_stats)
    assert post_volume < pre_volume * 0.3, (
        f"volume did not collapse: {post_volume:.0f} vs pre {pre_volume:.0f}"
    )

    # ...while unmet demand persists (people want bread at the legal price)...
    pre_unfilled = statistics.mean(s.unfilled_demand for s in pre_stats[3:])
    post_unfilled = statistics.mean(s.unfilled_demand for s in post_stats)
    assert post_unfilled > max(pre_unfilled * 3, 20), (
        f"no shortage signal: {post_unfilled:.0f} unfilled vs pre {pre_unfilled:.0f}"
    )

    # ...and sellers are visibly withdrawing (asks rejected by the price control).
    assert sum(s.suppressed_orders for s in post_stats) > 0


@pytest.mark.parametrize("seed", SEEDS)
def test_ceiling_repeal_restores_the_market(seed):
    """The Week 3 resolution beat: repealing the decree brings bread back."""
    scenario = bread_ceiling(seed=seed)
    world = scenario.world
    world.schedule(17, lambda w: w.repeal_price_ceiling("bread"))
    scenario.total_days = 26
    scenario.run()

    post_repeal = [s for s in world.stats_for("bread") if s.day >= 19]
    assert sum(s.volume for s in post_repeal) > 0, "market never recovered after repeal"

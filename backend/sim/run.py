"""Run headless economy scenarios and print day-by-day market tables.

Usage (from backend/):
    python -m sim.run                 # run all scenarios
    python -m sim.run festival_rush   # run one
"""
from __future__ import annotations

import sys

from .scenarios import ALL, Scenario


def print_report(scenario: Scenario) -> None:
    world = scenario.world
    print(f"\n=== {scenario.name} ===  notes: {scenario.notes}")
    for good in world.goods:
        print(f"\n  [{good}]")
        print(f"  {'day':>3} {'open':>6} {'high':>6} {'low':>6} {'close':>6} "
              f"{'vol':>5} {'unfilled_bid':>12} {'suppressed':>10}")
        for s in world.stats_for(good):
            fmt = lambda v: "-" if v is None else str(v)
            print(f"  {s.day:>3} {fmt(s.open):>6} {fmt(s.high):>6} {fmt(s.low):>6} "
                  f"{fmt(s.close):>6} {s.volume:>5} {s.unfilled_demand:>12} "
                  f"{s.suppressed_orders:>10}")


def main() -> None:
    names = sys.argv[1:] or list(ALL)
    for name in names:
        if name not in ALL:
            sys.exit(f"unknown scenario {name!r}; choose from {sorted(ALL)}")
        scenario = ALL[name]()
        scenario.run()
        print_report(scenario)


if __name__ == "__main__":
    main()

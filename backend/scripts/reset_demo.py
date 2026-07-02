"""Rotate the demo world by hand — same blue-green code path as the worker's
nightly cron (app.worker.demo_reset), minus the freshness guard.

Seeds a fresh mid-course world as an unflagged candidate, then flips is_demo
to it in one short transaction and retires the old world. A seed that fails
mid-run leaves the current demo untouched — rerun whenever.

    .venv/bin/python scripts/reset_demo.py

Point AGORA_DATABASE_URL at prod's public proxy to rotate the live demo
(see docs/DEPLOY.md). Note: over the public proxy the long seed can drop;
the safe flip means a retry costs nothing.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.worker import demo_reset  # noqa: E402


if __name__ == "__main__":
    rotated = asyncio.run(demo_reset({}, force=True))
    if rotated:
        print("\ndemo reset complete — /?demo=student lands in the new world")
    else:
        sys.exit("demo reset did NOT complete (seed failed?) — the previous "
                 "demo world is still live; see errors above and rerun.")

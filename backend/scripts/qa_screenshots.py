"""Playwright sweep: log in as QA student + instructor, screenshot every view.

Usage (from backend/):
    .venv/bin/python scripts/qa_screenshots.py [--suffix ""] [--out ../qa/shots]

Requires the docker compose stack on :5173 and a seeded world
(scripts/seed_midcourse.py). Saves PNGs + a console-error log per page.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
PASSWORD = "agora-qa"

STUDENT_PLACES = ["Market Square", "Your Shop", "Workshop", "The Docks",
                  "Daily Ledger", "The Crier", "Guild Hall", "Leaderboards"]
INSTRUCTOR_TABS = ["dashboard", "feed", "interventions", "heatmap",
                   "gradebook", "playbook"]


def login_token(pw, email: str) -> str:
    ctx = pw.request.new_context()
    r = ctx.post(f"{BASE}/api/auth/login",
                 data={"email": email, "password": PASSWORD})
    assert r.ok, f"login failed for {email}: {r.status} {r.text()}"
    return r.json()["token"]


def main(suffix: str, out: str) -> None:
    os.makedirs(out, exist_ok=True)
    tag = f"qa{suffix}"
    errors: dict[str, list[str]] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def new_page(token: str, mobile: bool = False):
            ctx = browser.new_context(
                viewport={"width": 390, "height": 844} if mobile
                else {"width": 1440, "height": 940},
                device_scale_factor=2,
            )
            ctx.add_init_script(
                f"localStorage.setItem('agora_token', '{token}')")
            page = ctx.new_page()
            page.on("console", lambda m: errors.setdefault(
                page.url + ":" + (shotname[0] or "?"), []).append(m.text)
                if m.type == "error" else None)
            return ctx, page

        shotname = [""]

        def shot(page, name: str, settle_ms: int = 900):
            shotname[0] = name
            page.wait_for_timeout(settle_ms)
            page.screenshot(path=f"{out}/{name}.png", full_page=True)
            print(f"  📸 {name}")

        # ---------- logged-out auth screen ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 940},
                                  device_scale_factor=2)
        page = ctx.new_page()
        page.goto(BASE)
        shot(page, "00-auth")
        page.goto(f"{BASE}/landing/")
        shot(page, "50-landing", settle_ms=1500)
        ctx.close()

        # landing page, phone width
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"{BASE}/landing/")
        shot(page, "51-landing-mobile", settle_ms=1500)
        ctx.close()

        # ---------- student sweep ----------
        stoken = login_token(pw, f"{tag}.student00@agora-u.edu")
        ctx, page = new_page(stoken)
        page.goto(BASE)
        page.wait_for_selector(".topbar", timeout=15000)
        shot(page, "10-student-default")
        for i, place in enumerate(STUDENT_PLACES):
            try:
                page.click(f".place-tile:has-text('{place}')", timeout=5000)
                shot(page, f"1{i+1}-student-{place.lower().replace(' ', '-')}")
            except Exception as e:
                print(f"  ⚠️ {place}: {type(e).__name__}")
        # market with a storied good selected (bread: drought + decree history)
        try:
            page.click(".place-tile:has-text('Market Square')")
            page.wait_for_timeout(600)
            for sel in ["text=Bread", "text=bread"]:
                try:
                    page.click(sel, timeout=2500)
                    break
                except Exception:
                    continue
            shot(page, "19-student-market-bread")
        except Exception as e:
            print(f"  ⚠️ market-bread: {type(e).__name__}")
        # Pip chat dock open (avatar button), then the quiz pane
        try:
            page.click(".pip-avatar", timeout=4000)
            shot(page, "20-student-pip-open")
            page.click("button:has-text('quiz me')", timeout=3000)
            shot(page, "21-student-pip-quiz")
        except Exception as e:
            print(f"  ⚠️ pip: {type(e).__name__}")
        ctx.close()

        # ---------- student, phone viewport ----------
        ctx, page = new_page(stoken, mobile=True)
        page.goto(BASE)
        page.wait_for_selector(".topbar", timeout=15000)
        shot(page, "30-mobile-default")
        for place in ["Market Square", "Daily Ledger"]:
            try:
                page.click(f".place-tile:has-text('{place}')", timeout=5000)
                shot(page, f"31-mobile-{place.lower().replace(' ', '-')}")
            except Exception as e:
                print(f"  ⚠️ mobile {place}: {type(e).__name__}")
        ctx.close()

        # ---------- instructor sweep ----------
        itoken = login_token(pw, f"{tag}.instructor@agora-u.edu")
        ctx, page = new_page(itoken)
        page.goto(BASE)
        try:
            page.click("button:has-text('Enter')", timeout=8000)
        except Exception:
            print("  ⚠️ instructor world picker: no Enter button (auth/me fix live?)")
        for i, tab in enumerate(INSTRUCTOR_TABS):
            try:
                page.click(f".place-tile:has-text('{tab}')", timeout=5000)
                if tab == "playbook":
                    try:
                        page.click("button:has-text('Generate')", timeout=3000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        pass
                shot(page, f"4{i}-instructor-{tab}")
            except Exception as e:
                print(f"  ⚠️ {tab}: {type(e).__name__}")
        ctx.close()
        browser.close()

    with open(f"{out}/console-errors.json", "w") as f:
        json.dump(errors, f, indent=2)
    print(f"\ndone → {out} ({len(os.listdir(out))} files)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default="")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(__file__), "..", "..", "qa", "shots"))
    args = ap.parse_args()
    main(args.suffix, os.path.abspath(args.out))

"""Playwright matrix sweep: every screen, both roles, desktop + phone,
clean-slate through late-course, plus a live god-mode disruption.

Usage (from backend/):
    .venv/bin/python scripts/qa_screenshots.py [--out ../qa/shots] [--only PREFIX]

Expects worlds seeded by seed_midcourse.py with suffixes w1 (clean), w2, w4,
w5, w6, w7 (password agora-qa). Saves PNGs + console-errors.json.
"""
from __future__ import annotations

import argparse
import json
import os

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
PASSWORD = "agora-qa"
DESKTOP = {"width": 1440, "height": 940}
PHONE = {"width": 390, "height": 844}

errors: dict[str, list[str]] = {}
current = [""]


def login(pw, email):
    ctx = pw.request.new_context()
    r = ctx.post(f"{BASE}/api/auth/login", data={"email": email, "password": PASSWORD})
    assert r.ok, f"login failed {email}: {r.status} {r.text()}"
    return r.json()["token"]


class Sweep:
    def __init__(self, browser, out, only):
        self.browser, self.out, self.only = browser, out, only

    def page(self, token=None, phone=False):
        ctx = self.browser.new_context(
            viewport=PHONE if phone else DESKTOP, device_scale_factor=2,
            reduced_motion="reduce")
        if token:
            ctx.add_init_script(f"localStorage.setItem('agora_token','{token}')")
        p = ctx.new_page()
        p.on("console", lambda m: errors.setdefault(current[0], []).append(m.text)
             if m.type == "error" else None)
        return ctx, p

    def shot(self, p, name, settle=900, full=True):
        if self.only and not name.startswith(self.only):
            return
        current[0] = name
        p.wait_for_timeout(settle)
        p.screenshot(path=f"{self.out}/{name}.png", full_page=full)
        print(f"  📸 {name}")

    def place(self, p, label):
        p.click(f".place-tile:has-text('{label}')", timeout=6000)


def main(out, only):
    os.makedirs(out, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        s = Sweep(browser, out, only)

        def student(suffix, n="00"):
            return login(pw, f"qa{suffix}.student{n}@agora-u.edu")

        def instructor(suffix):
            return login(pw, f"qa{suffix}.instructor@agora-u.edu")

        # ---------- logged out ----------
        ctx, p = s.page()
        p.goto(BASE); s.shot(p, "00-auth")
        p.goto(f"{BASE}/landing/"); s.shot(p, "01-landing", settle=1600)
        ctx.close()
        ctx, p = s.page(phone=True)
        p.goto(f"{BASE}/landing/"); s.shot(p, "02-landing-mobile", settle=1600)
        ctx.close()

        # ---------- week 1: clean slate ----------
        try:
            tok = student("w1")
            ctx, p = s.page(tok)
            p.goto(BASE); p.wait_for_selector(".topbar", timeout=15000)
            s.shot(p, "w1-10-student-day-one")
            try:
                s.place(p, "Traveling Merchant")
                s.shot(p, "w1-11-merchant-minigame")
            except Exception as e:
                print(f"  ⚠️ merchant: {type(e).__name__}")
            s.place(p, "The Crier"); s.shot(p, "w1-12-crier-empty")
            s.place(p, "Workshop"); s.shot(p, "w1-13-workshop-empty")
            ctx.close()
            ctx, p = s.page(instructor("w1"))
            p.goto(BASE); s.shot(p, "w1-20-instructor-day-one", settle=1400)
            ctx.close()
        except AssertionError as e:
            print(f"  ⚠️ w1 world missing: {e}")

        # ---------- week 4: the deep sweep ----------
        tok = student("w4")
        ctx, p = s.page(tok)
        p.goto(BASE); p.wait_for_selector(".topbar", timeout=15000)
        s.shot(p, "w4-10-market")
        try:
            p.click("text=Bread", timeout=3000)
            s.shot(p, "w4-11-market-bread")
        except Exception:
            pass
        for label, name in [("Your Shop", "w4-12-shop"), ("Workshop", "w4-13-workshop"),
                            ("The Docks", "w4-14-docks"), ("Daily Ledger", "w4-15-puzzle"),
                            ("The Crier", "w4-16-crier"), ("Guild Hall", "w4-17-guild"),
                            ("Leaderboards", "w4-18-boards")]:
            try:
                s.place(p, label); s.shot(p, name)
            except Exception as e:
                print(f"  ⚠️ {label}: {type(e).__name__}")
        try:
            p.click(".pip-avatar", timeout=4000); s.shot(p, "w4-19-pip-chat")
            p.click("button:has-text('quiz me')", timeout=3000)
            s.shot(p, "w4-19b-pip-quiz")
        except Exception as e:
            print(f"  ⚠️ pip: {type(e).__name__}")
        ctx.close()

        # week 4 student, phone
        ctx, p = s.page(tok, phone=True)
        p.goto(BASE); p.wait_for_selector(".topbar", timeout=15000)
        s.shot(p, "w4-30-mobile-market")
        for label, name in [("The Docks", "w4-31-mobile-docks"),
                            ("Daily Ledger", "w4-32-mobile-puzzle"),
                            ("The Crier", "w4-33-mobile-crier"),
                            ("Leaderboards", "w4-34-mobile-boards")]:
            try:
                s.place(p, label); s.shot(p, name)
            except Exception as e:
                print(f"  ⚠️ mobile {label}: {type(e).__name__}")
        ctx.close()

        # week 4 instructor, desktop + phone
        itok = instructor("w4")
        ctx, p = s.page(itok)
        p.goto(BASE); p.wait_for_timeout(800)
        s.shot(p, "w4-40-dashboard", settle=1200)
        for tab, name in [("feed", "w4-41-feed"), ("interventions", "w4-42-interventions"),
                          ("heatmap", "w4-43-heatmap"), ("gradebook", "w4-44-gradebook")]:
            try:
                s.place(p, tab); s.shot(p, name)
            except Exception as e:
                print(f"  ⚠️ {tab}: {type(e).__name__}")
        ctx.close()
        ctx, p = s.page(itok, phone=True)
        p.goto(BASE); p.wait_for_timeout(1000)
        s.shot(p, "w4-50-mobile-dashboard", settle=1200)
        for tab, name in [("feed", "w4-51-mobile-feed"),
                          ("interventions", "w4-52-mobile-interventions")]:
            try:
                s.place(p, tab); s.shot(p, name)
            except Exception as e:
                print(f"  ⚠️ mobile {tab}: {type(e).__name__}")
        ctx.close()

        # ---------- god mode: a live disruption in the w2 world ----------
        try:
            itok2 = instructor("w2")
            ctx, p = s.page(itok2)
            p.goto(BASE); p.wait_for_timeout(900)
            s.place(p, "interventions")
            p.wait_for_timeout(600)
            p.click(".place-tile:has-text('price ceiling')", timeout=5000)
            p.wait_for_timeout(400)
            p.select_option(".form-grid select", label="Bread")
            s.shot(p, "god-60-ceiling-form", settle=400)
            p.click("button:has-text('Preview impact')")
            s.shot(p, "god-61-ceiling-preview", settle=900)
            p.click("button:has-text('Execute now')")
            s.shot(p, "god-62-ceiling-executed", settle=1100)
            s.place(p, "feed")
            s.shot(p, "god-63-feed-after", settle=1000)
            ctx.close()
            # what the student sees afterward
            ctx, p = s.page(student("w2"))
            p.goto(BASE); p.wait_for_selector(".topbar", timeout=15000)
            s.place(p, "The Crier")
            s.shot(p, "god-64-student-crier-decree")
            s.place(p, "Market Square")
            p.click("text=Bread", timeout=3000)
            s.shot(p, "god-65-student-bread-ceiling")
            ctx.close()
        except Exception as e:
            print(f"  ⚠️ god-mode sequence: {type(e).__name__}: {e}")

        # ---------- late course: smog, fishery, tournament ----------
        for sfx, shots in [("w6", [("Market Square", "w6-70-smog-market"),
                                   ("The Docks", "w6-71-docks-fishery")]),
                           ("w7", [("Guild Hall", "w7-72-guild-compacts"),
                                   ("Leaderboards", "w7-73-tournament-boards")])]:
            try:
                ctx, p = s.page(student(sfx))
                p.goto(BASE); p.wait_for_selector(".topbar", timeout=15000)
                for label, name in shots:
                    try:
                        s.place(p, label); s.shot(p, name)
                    except Exception as e:
                        print(f"  ⚠️ {sfx} {label}: {type(e).__name__}")
                ctx.close()
            except AssertionError:
                print(f"  ⚠️ {sfx} world missing")

        browser.close()
    with open(f"{out}/console-errors.json", "w") as f:
        json.dump(errors, f, indent=2)
    print(f"\ndone → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(__file__), "..", "..", "qa", "shots"))
    ap.add_argument("--only", default=None, help="only shots starting with prefix")
    args = ap.parse_args()
    main(os.path.abspath(args.out), args.only)

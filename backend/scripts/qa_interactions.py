"""Interaction QA: actually PLAY the game in a browser and screenshot results.

Covers paths the static sweep never exercises: order fills, gather/craft,
fishing casts, puzzle guesses, tutor checks, live Pip chat (real LLM), Opus
playbook generation, the epilogue recap, and the demo tour on a phone.

Usage (from backend/):  .venv/bin/python scripts/qa_interactions.py [--out DIR]
Needs: stack on :5173, demo world (--demo), qaw5/qaw7 worlds seeded.
"""
from __future__ import annotations

import argparse
import os

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
PASSWORD = "agora-qa"


def main(out: str) -> None:
    os.makedirs(out, exist_ok=True)
    shots: list[str] = []

    with sync_playwright() as pw:
        b = pw.chromium.launch()

        def login(email):
            return b.new_context().request.post(
                f"{BASE}/api/auth/login",
                data={"email": email, "password": PASSWORD}).json()["token"]

        def page(token=None, phone=False):
            ctx = b.new_context(
                viewport={"width": 390, "height": 844} if phone
                else {"width": 1440, "height": 940}, device_scale_factor=2)
            if token:
                ctx.add_init_script(
                    f"localStorage.setItem('agora_token','{token}')")
            return ctx, ctx.new_page()

        def shot(p, name, settle=900):
            p.wait_for_timeout(settle)
            p.screenshot(path=f"{out}/{name}.png")
            shots.append(name)
            print(f"  📸 {name}")

        # ---------- play a session as a fresh demo visitor ----------
        ctx, p = page()
        p.goto(f"{BASE}/?demo=student")
        p.wait_for_selector(".tour-card", timeout=20000)
        p.click(".tour-card .dismiss")  # skip tour; we're here to play
        p.wait_for_timeout(400)

        # market buy: 5 grain at market price -> should fill instantly vs NPCs
        p.click("button:has-text('Buy 5 grain')")
        shot(p, "ix-10-market-buy-filled", settle=700)

        # workshop: gather aptitude good, craft flour from bought grain
        p.click(".place-tile:has-text('Workshop')")
        p.wait_for_timeout(500)
        p.click("button:has-text('Gather')")
        shot(p, "ix-11-gathered", settle=700)
        crafts = p.locator("button:has-text('craft')")
        if crafts.count() > 0:
            crafts.first.click()
            shot(p, "ix-12-crafted", settle=700)

        # docks: cast a line (1.1s suspense built in)
        p.click(".place-tile:has-text('The Docks')")
        p.wait_for_timeout(400)
        p.click("button:has-text('Cast')")
        shot(p, "ix-13-fishing-result", settle=2300)

        # puzzle: one real guess
        p.click(".place-tile:has-text('Daily Ledger')")
        p.wait_for_timeout(500)
        p.fill("input[placeholder='10–99']", "55")
        p.click("button:has-text('Guess')")
        shot(p, "ix-14-puzzle-guess", settle=700)

        # pip: take the quiz (MCQ or free), answer choice A / a sentence
        p.click(".pip-avatar")
        p.wait_for_timeout(400)
        p.click("button:has-text('quiz me')")
        p.wait_for_timeout(800)
        if p.locator(".pip-dock textarea").count() > 0:
            p.fill(".pip-dock textarea",
                   "Because the drought cut grain supply, costs rose and "
                   "sellers raised prices.")
        else:
            p.locator(".pip-dock button:has-text('A.')").click()
        p.click("button:has-text('Answer')")
        shot(p, "ix-15-check-answered", settle=2500)

        # pip: live chat (real Sonnet if key set; canned otherwise)
        p.click(".pip-dock button:has-text('chat')")
        p.fill("input[placeholder='Ask Pip…']",
               "Why did bread get so expensive during the drought?")
        p.keyboard.press("Enter")
        try:
            # one user msg + one real tutor reply ('.muted' is the busy
            # indicator — don't count it)
            p.wait_for_function(
                "document.querySelectorAll('.pip-chat .msg:not(.muted)')"
                ".length >= 2", timeout=60000)
        except Exception:
            print("  ⚠️ pip chat reply timed out")
        shot(p, "ix-16-pip-chat-live", settle=400)
        ctx.close()

        # ---------- instructor: real Opus playbook ----------
        ctx, p = page(login("qademo2.instructor@agora-u.edu"))
        p.goto(BASE)
        p.wait_for_timeout(900)
        p.click(".place-tile:has-text('playbook')")
        p.wait_for_timeout(400)
        p.click("button:has-text('Generate')")
        try:
            # the rendered playbook's own H3 ('Lecture Playbook — Week N');
            # beware: page copy also contains the words 'what happened'
            p.wait_for_selector("h3:has-text('— Week')", timeout=150000)
        except Exception:
            print("  ⚠️ playbook generation timed out")
        shot(p, "ix-20-playbook-opus", settle=1200)
        ctx.close()

        # ---------- epilogue: end w7 and read a student's story ----------
        itok = login("qaw7.instructor@agora-u.edu")
        rc = b.new_context().request
        me = rc.get(f"{BASE}/api/auth/me",
                    headers={"Authorization": f"Bearer {itok}"}).json()
        wid = me["worlds"][0]["world_id"]
        r = rc.post(f"{BASE}/api/worlds/{wid}/instructor/state",
                    headers={"Authorization": f"Bearer {itok}"},
                    data={"state": "epilogue"})
        print(f"  epilogue set: {r.status}")
        ctx, p = page(login("qaw7.student00@agora-u.edu"))
        p.goto(BASE)
        p.wait_for_selector(".topbar", timeout=15000)
        p.click(".place-tile:has-text('Your Story')")
        shot(p, "ix-21-epilogue-recap", settle=1800)
        ctx.close()

        # ---------- w5: a license-holding tycoon's guild hall ----------
        ctx, p = page(login("qaw5.student03@agora-u.edu"))
        p.goto(BASE)
        p.wait_for_selector(".topbar", timeout=15000)
        p.click(".place-tile:has-text('Guild Hall')")
        shot(p, "ix-22-tycoon-guild-license")
        ctx.close()

        # ---------- phone: demo entry, tour, then a real order ----------
        ctx, p = page(phone=True)
        p.goto(f"{BASE}/?demo=student")
        p.wait_for_selector(".tour-card", timeout=20000)
        shot(p, "ix-30-mobile-tour", settle=600)
        p.click(".tour-card .dismiss")
        p.wait_for_timeout(400)
        p.click("button:has-text('Buy 5 grain')")
        shot(p, "ix-31-mobile-buy-filled", settle=700)
        ctx.close()

        b.close()
    print(f"\ndone → {out} ({len(shots)} shots)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(__file__), "..", "..", "qa", "interactions"))
    args = ap.parse_args()
    main(os.path.abspath(args.out))

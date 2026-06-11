# Instructor Automation — push-first strategy

Premise (2026-06-11): professors don't want to hang out in our game. They want
to know what their students learned and when to intervene, with as close to
zero logins as possible. Everything instructor-facing should default to
**push** (email, LMS) with the dashboard as the opt-in deep-dive, not the
front door.

## What is automated today

| Need | How it's served | Login needed? |
|---|---|---|
| Weekly lecture prep | **Monday Brief** email: playbook + class summary + at-risk students + gradebook CSV attached | No |
| Grades into the LMS | CSV attached to the Brief (imports into Canvas/Moodle/Blackboard) or `gradebook.csv` endpoint | No (attachment) |
| Course pacing | Calendar-paced worlds close daily and advance weeks via the worker; script beats (festival, drought, ceiling, auctions, tournament) fire on schedule | No |
| Sign-in when they do visit | Magic link by email | — |

### Monday Brief mechanics
- `advance_week` stamps `world.config.digest_due_week` (covers both the
  worker's calendar close and a manual advance).
- The worker's `email_sweep` cron (every 10 min) calls
  `services/digest.process_due_digests`: builds the brief **outside** the
  close transaction, sends, then stamps `digest_sent_week` under a row lock.
  Idempotent; failures retry on the next sweep; `email_log` is the audit
  trail.
- Opt-out: `world.config.email_digest = false` (toggle in the Playbook tab).
  Manual "send me this week's brief now" endpoint exists for demos and
  re-sends. Demo worlds never email.
- Transport: `services/email.py` — `console` (dev: logged + stored in
  `email_log.body_text`) or `resend` (HTTPS API, works on Railway; set
  `AGORA_EMAIL_PROVIDER=resend`, `AGORA_RESEND_API_KEY`, `AGORA_EMAIL_FROM`,
  `AGORA_APP_BASE_URL`).

## LTI 1.3: deferred — decision and rationale

**Decision: do not build LTI now.** Revisit after 2–3 real course
deployments.

- The minimal credible build is OIDC launch + AGS score push (+ Deep Linking
  to create the line item). `pylti1p3` only ships Django/Flask adapters, so
  FastAPI needs a custom adapter (~200 lines). Realistic effort is **3–4
  weeks**, dominated not by code but by per-LMS platform registration
  (Canvas developer keys, Moodle external-tool setup — an *institutional
  admin* action) and interop testing.
- The product goal ("professor never logs in") is already met by the CSV
  attachment: every major LMS imports gradebook CSV, and our gradebook is
  keyed on institutional email by design (`pedagogy/grades.py`).
- Groundwork already in place for the eventual AGS pusher:
  `GET /worlds/{id}/instructor/scores` returns the stable, LMS-agnostic shape
  `{email, score, max_score, world_week}`. No speculative schema beyond that
  (no lms_user_id columns, no JWKS stubs) until a partner LMS exists.

## Next automation candidates (in order)

1. **Alert emails, batched per close** (~40 lines): detectors only run at the
   daily close, so "immediate" alerts don't exist — at most one batch per
   world-day. Extend `email_sweep`: if `severity == "alert"` moments exist
   with `world_day > config.alerts_sent_through_day` and
   `config.email_alerts` is on, send one compact email and stamp. Reuses all
   Monday Brief machinery.
2. **Disengagement nudge**: when `active_players` collapses mid-course,
   email the instructor a one-liner with the at-risk roster (the digest
   already lists individuals weekly; this is the mid-week safety net).
3. **End-of-course recap email**: epilogue triggers a final brief with the
   full-semester arc and final gradebook.

## What deliberately stays manual

- **Ceiling repeals and other "live in lecture" moments** — the playbook
  suggests doing these in class on purpose; automating them destroys the
  teaching beat.
- **Targeted interventions** (antitrust against a specific student, licenses,
  fines) — judgment calls.
- **Grade weights, week pacing for manual-paced worlds, ending the world** —
  consequential, infrequent, one click each.

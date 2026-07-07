# Agora — Loom tour script

~10 min internal walkthrough. **Cold open + outro are talk-to-camera; the middle
is a glance-and-go table.** While recording: read the left cell (what to click),
say the **bolded line**, move on. One beat per row.

- **SHOW** = what's on screen / what to click
- **SAY** = the beat — **bold = the one line that must land**
- ★ = centerpiece, slow down here

Tabs open before you start: `/?demo=student`, `/?demo=instructor`, `/landing/`.

Clock: open ~1.25m · landing ~1.5m · student ~4m · faculty ~3m · outro ~1.5m ≈ **11m**.
Running long? Cut the minigames row and the decree row first.

---

## 0. Cold open — READ THIS — ~1.25 min

> To camera, or a black slide with just *Agora*. Don't show the app yet.

"Quick one. I think we're at the start of a Cambrian explosion in course
materials, and I built something to show you what I mean.

For a century the unit of content was the textbook. Then it became 'courseware' —
MyLab, McGraw-Hill Connect — which, if you're honest, is the same textbook with a
homework engine and an autograder bolted on. Still fundamentally a book you click
through. **What comes next won't look like a textbook, and it won't even look like
courseware.** AI has collapsed the cost of building genuinely interactive,
discipline-specific experiences to almost nothing — so we're about to see a wave
of AI-native products that teach in ways a book simply can't.

To make that concrete, I built one. It's called Agora — a full economics course
where students don't *read about* a market, they live inside a real, working one,
with their whole class, all term. Two things to know: everything you'll see is
**real, live AI running in production** — the tutor, the grading, the lecture
prep, none of it mocked up. And it was built by one person in a few weeks,
essentially **100% with Fable.**

I'm not taking this to market — it's a proof of what's buildable now. Let me show
you the thing, and I'll come back at the end to why I think it should scare the
incumbents. Let's start where a professor would — the landing page."

> → share `/landing/`, top.

---

## 1. Landing page — ~1.5 min · *scroll slow, one beat per section*

| SHOW | SAY |
|---|---|
| Hero + art | Multiplayer: **whole class, one shared economy, real time.** Art's all Gemini pipeline, Wingspan look *(one line, move)* |
| "Every mechanic is a syllabus concept" | **No gamification bolted on — every mechanic *is* a concept.** Order book = supply/demand · decree = price ceiling · fishery = commons. *Can't play without doing econ.* |
| "Seven-week arc" *(scroll, don't list all nine)* | **A story, not a sandbox.** Drought → Bread Decree: the class *feels* the shortage. **Can't get that from a problem set.** |
| OpenStax + assessment *(blow past fast)* | **OpenStax 3e-mapped · 171 items / 30 objectives · Bloom-tagged.** → "real Monday Brief's on the faculty side — let's play." |

> → switch to `/?demo=student`.

---

## 2. Student — living in the market — ~4 min

*Land mid-course. Say it: "week 4, 12 classmates, live market, a history behind me."*

**Quick tour (~2 min)**

| SHOW | SAY |
|---|---|
| Order book — place one order | Real **double-auction with escrow.** Point at a moved price: **"I didn't set this — the class did."** Hardest thing to teach from a book |
| Workshop → your shop | Buy inputs, run a recipe, sell = the supply side. **"Run the second oven today?" *is* fixed vs. variable cost.** Shop's already made sales |
| Common Threads + Fishing *(don't rush)* | Reasons to **show up every day**: puzzle, fishing, haggling, streaks. **A textbook can't and courseware won't — it was never worth funding. Now it's ~free, so why not.** Fishery's still a commons |

**★ Pip + Study — the centerpiece (~2 min, slow down)**

| SHOW | SAY |
|---|---|
| Open Pip → "why did bread spike this week?" | **Live, on Claude Sonnet.** Socratic, 24/7, knows *this* world — nudges toward the reasoning, doesn't hand over the answer |
| Study → written check · answer *slightly wrong term* | **Mastery bars move live, on the page.** Grades **the economics, not the jargon** — "marginal utility" for "product" costs ~nothing. Fast, on Haiku |
| Refine loop — improve it / ask a clarifying Q | **Revision is rewarded — the score goes up.** Ask a clarifying Q mid-check, grade holds. **Assessment as a conversation** |
| One MCQ → show the explanation | Wrong answer → **why right is right, why the trap tempts.** Items are **self-contained: economics, not Agora trivia** |

> → "every action's becoming *evidence* — which is what the professor sees. Flip sides."

---

## 3. Faculty — you run the world, Monday's easy — ~3 min

*Framing: "You don't play the game. You run the world." Everything here saves time.*

| SHOW | SAY |
|---|---|
| Heatmap, full screen *(~1m)* | **Most valuable screen: whole class × whole syllabus, one glance.** Click a weak objective → who, how weak, what to ask. Auto-opens the weakest |
| ★ Monday Brief email *(~1m)* | **In their inbox every Monday, before they log in.** 60-sec version: the story ("flour up 32%") · weakest objectives · at-risk students by name · gradebook CSV attached |
| Lecture playbook *(~45s)* | **Discussion questions aimed at *this* class's gaps,** built on the events they lived through. Generated with Opus. Editable, pick the week |
| *(optional — cut if long)* Decree / price ceiling | Cap bread this morning → section's lived a shortage by class time. **Tuesday's news = Wednesday's experiment** |

> → "That's Agora end to end. Let me zoom out — the product isn't the point."

---

## 4. Outro — the payoff — ~1.5 min · *talk to camera, give it room*

- **Callback:** "I promised you the part that should scare the incumbents."
- **Cost is the whole argument:** a full multiplayer app — live markets, LLM tutor, autograder, lecture prep, weekly email — **one person, a few weeks, ~all Fable.** Prod on Railway, 3 Claude models. *Five years ago: a funded team and a year.*
- **Why it's not a textbook:** AI let the **medium finally fit the discipline.** Econ needs a live market — you *feel* a shortage, you can't read one. **Music theory wants something else. Cog psych, something else again.**
- **The moat:** incumbents' moat was the **content library** — the textbook, the item bank. Generate a Bloom-tagged bank *and* the experience in weeks → **that moat is a puddle.** New moat = **knowing which medium fits which subject.**
- **The ask:** which lanes, which disciplines — what do we build, buy, or partner before faculty expect *this* instead of a PDF?
- Thanks — happy to give a live walkthrough or the repo.

---

## Appendix — backup lines (grab if you stall)

- **Learning science:** market *is* the textbook · mastery = Bloom-tagged EMA, warm-started · refine = growth mindset · grade economics not vocab · self-contained = transfer · participation ≠ wealth.
- **Delight (the "~free now" point):** puzzle/fishing/haggling/streaks = reasons to log in · textbooks can't, courseware won't · cheap to build now, so motivation stops being a luxury.
- **Faculty:** heatmap = 10-sec diagnosis · Monday Brief = never log in · playbook = prep on their actual gaps · CSV → any LMS · auto-grades free response *and* MCQ.
- **Tech:** ~100% Fable · Railway (FastAPI + React + Postgres + worker) · Sonnet tutor / Haiku grading / Opus playbooks · Gemini art · every AI path degrades gracefully.
- **Meta:** won't look like textbooks *or* courseware · medium fits discipline · content-library moat is a puddle · new moat = which medium fits which subject.

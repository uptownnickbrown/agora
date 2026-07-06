"""Draft per-item answer explanations for the MCQ bank, then commit them.

Fills ONLY the ids missing from bank_explanations.EXPLANATIONS, so reruns are
cheap and hand-edits survive. Writes the merged dict back to
app/pedagogy/bank_explanations.py for review before committing.

Usage (from backend/, needs AGORA_ANTHROPIC_API_KEY):
    .venv/bin/python scripts/gen_explanations.py
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.pedagogy.bank import LEARNING_OBJECTIVES, QUESTIONS  # noqa: E402
from app.pedagogy.bank_explanations import EXPLANATIONS  # noqa: E402

SYSTEM = (
    "You write the one-line explanation a student sees right after answering "
    "a multiple-choice question in an intro microeconomics course. In at most "
    "40 words: say crisply why the correct choice is right, and if one wrong "
    "choice is a classic trap, name why it tempts. Plain language, ordinary "
    "punctuation, no em-dashes, no bird or animal voice, no preamble. Output "
    "the explanation sentence(s) only.")

CONCURRENCY = 8


async def draft(client, model, q) -> tuple[str, str]:
    lo_text = "; ".join(LEARNING_OBJECTIVES[lo].text for lo in q.los
                        if lo in LEARNING_OBJECTIVES)
    choices = "\n".join(f"{'*' if i == q.answer else ' '} {c}"
                        for i, c in enumerate(q.choices))
    msg = (f"OBJECTIVE: {lo_text}\nQUESTION: {q.prompt}\n"
           f"CHOICES (* = correct):\n{choices}")
    r = await client.messages.create(
        model=model, max_tokens=120,
        system=[{"type": "text", "text": SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": msg}])
    text = next((b.text for b in r.content if b.type == "text"), "").strip()
    return q.id, text.replace("—", ",").replace(" ,", ",")


async def main() -> None:
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        sys.exit("AGORA_ANTHROPIC_API_KEY is not set")
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    todo = [q for q in QUESTIONS.values()
            if q.kind == "mcq" and q.id not in EXPLANATIONS]
    print(f"{len(todo)} items to draft ({len(EXPLANATIONS)} already committed)")
    out = dict(EXPLANATIONS)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(q):
        async with sem:
            qid, text = await draft(client, settings.model_tutor, q)
            if text:
                out[qid] = text
                print(f"  {qid}: {text[:90]}")

    await asyncio.gather(*(one(q) for q in todo))

    path = pathlib.Path(__file__).resolve().parents[1] / "app" / "pedagogy" / \
        "bank_explanations.py"
    header = path.read_text().split("EXPLANATIONS")[0]
    lines = ["EXPLANATIONS: dict[str, str] = {"]
    for qid in sorted(out):
        text = out[qid].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    "{qid}":\n        "{text}",')
    lines.append("}")
    path.write_text(header + "\n".join(lines) + "\n")
    print(f"wrote {len(out)} explanations to {path}")


if __name__ == "__main__":
    asyncio.run(main())

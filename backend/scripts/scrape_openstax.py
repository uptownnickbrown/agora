"""Refresh app/pedagogy/openstax.py from the OpenStax book (CC BY 4.0).

Pulls each course chapter's "Key Concepts and Summary" page from
*Principles of Microeconomics 3e* and rewrites the grounding module Pip uses
when generating practice questions.

    .venv/bin/python scripts/scrape_openstax.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

CHAPTERS = [2, 3, 5, 7, 8, 9, 10, 11, 12, 13]
BASE = ("https://openstax.org/books/principles-microeconomics-3e/pages/"
        "{}-key-concepts-and-summary")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "app", "pedagogy", "openstax.py")

HEADER = '''"""OpenStax grounding for Pip's generated questions.

Chapter "Key Concepts and Summary" text from *Principles of Microeconomics 3e*
by Steven A. Greenlaw, David Shapiro, and Daniel MacDonald (OpenStax, Rice
University), licensed CC BY 4.0 — https://openstax.org/details/books/principles-microeconomics-3e
(see docs/ATTRIBUTION.md). Scraped {date} by scripts/scrape_openstax.py;
rerun that script to refresh.

Used as source-of-truth context when Pip writes fresh practice questions, so
generated items stay aligned with the actual course text.
"""

CHAPTER_SUMMARIES: dict[int, str] = {{
'''


def main() -> None:
    out: dict[int, str] = {}
    for ch in CHAPTERS:
        html = urllib.request.urlopen(
            urllib.request.Request(BASE.format(ch),
                                   headers={"User-Agent": "Mozilla/5.0"}),
            timeout=30).read().decode()
        main_el = BeautifulSoup(html, "html.parser").find("main")
        if main_el is None:
            sys.exit(f"chapter {ch}: no <main> found — page layout changed?")
        text = main_el.get_text("\n", strip=True)
        text = text.split("Order a print copy")[0].strip()
        if len(text) < 800:
            sys.exit(f"chapter {ch}: suspiciously short ({len(text)} chars)")
        out[ch] = text
        print(f"  ch{ch}: {len(text)} chars")
        time.sleep(1)
    with open(OUT, "w") as f:
        f.write(HEADER.format(date=time.strftime("%Y-%m-%d")))
        for ch, text in out.items():
            f.write(f"    {ch}: {text!r},\n")
        f.write("}\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

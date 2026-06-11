#!/usr/bin/env python3
"""Addendum assets: the modern-shell backdrop, missing event paintings,
the recap laurel, and a workshop scene. Same pipeline as generate_assets.py.

    python3 scripts/generate_assets2.py            # everything
    python3 scripts/generate_assets2.py backdrop   # one family
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assetlib import CHROMA, STYLE, finalize, generate

EVENT = ("A storybook event illustration scene for the game's town "
         "newspaper, painted edge to edge as a full scene with absolutely no "
         "frame, no border, no curtains and no vignette — the painting runs "
         "off all four edges. ")


def gen(slot, prompt, w, h, *, aspect="1:1", size="2K", transparent=True,
        tol=130, pocket=150, margin=0.04):
    full = STYLE + " " + prompt + ((" " + CHROMA) if transparent else "")
    raw = generate(full, slot.replace("/", "_"), aspect=aspect, size=size)
    finalize(raw, slot, w, h, transparent=transparent, tolerance=tol,
             pocket_tolerance=pocket, margin=margin)


def family_backdrop():
    # The app shell's full-bleed environment. Deliberately calm: low contrast,
    # hazy, big quiet sky — UI panels must stay readable on top of it.
    gen("ui/backdrop_town",
        "A very wide, calm panoramic painting of a lightly fantastical "
        "pre-industrial Mediterranean market town seen from a gentle hill at "
        "soft dawn: muted red-roofed whitewashed houses, a small classical "
        "temple, olive trees, distant green hills fading into atmospheric "
        "haze. The lower third is the town and hills; the upper two thirds "
        "are a vast soft gradient sky in muted sage-green and warm cream "
        "tones with a few wispy clouds and two tiny distant pigeons. Soft "
        "diffuse light, low contrast, hazy and atmospheric like a quiet "
        "fresco — nothing busy, nothing sharp, painted edge to edge.",
        2048, 1100, aspect="21:9", size="4K", transparent=False)


def family_events():
    gen("events/merchant",
        EVENT + "The Traveling Merchant arrives: a cheerful traveling "
        "merchant with a weathered wide-brimmed hat leading a heavily-laden, "
        "unimpressed camel into the market square at morning, the camel "
        "stacked with colorful bundles, rolled carpets, hanging pots and "
        "bulging saddlebags, townsfolk turning to look, market awnings and "
        "columns behind.", 600, 340, aspect="16:9", transparent=False)
    gen("events/charter",
        EVENT + "The Charter Choice: a crossroads moment inside the guild "
        "hall — on the left side a grand blueprint easel showing a large "
        "factory building with tall chimneys (blank blueprint, no text), on "
        "the right side a humble artisan's workbench with fine handmade "
        "goods, and between them a thoughtful merchant scratching their "
        "head, a guild clerk in green robes presenting both options with "
        "open hands.", 600, 340, aspect="16:9", transparent=False)


def family_recap():
    gen("recap/laurel",
        "Flat storybook game icon, centered, no scene, no ground, no shadow: "
        "a graduation laurel — a green laurel wreath with small gold berries "
        "encircling a rolled cream parchment diploma tied with a terracotta "
        "ribbon bow.", 256, 256, size="1K")


def family_workshop():
    gen("places/workshop_scene",
        "A wide cozy interior scene of a pre-industrial artisan workshop in "
        "warm lamplight: a long wooden workbench with tools, a loom with "
        "sage-green cloth in progress by the window, sacks of grain and "
        "stacked lumber, a small glowing hearth, shelves of jars and "
        "finished goods, motes of dust in a sunbeam. Warm, industrious, "
        "inviting, painted edge to edge.",
        480, 280, aspect="16:9", transparent=False)


FAMILIES = {
    "backdrop": family_backdrop,
    "events": family_events,
    "recap": family_recap,
    "workshop": family_workshop,
}

if __name__ == "__main__":
    picks = sys.argv[1:] or list(FAMILIES)
    for p in picks:
        print(f"=== {p} ===")
        FAMILIES[p]()

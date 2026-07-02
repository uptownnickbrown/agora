#!/usr/bin/env python3
"""Caravan visitor portraits for the haggling minigame (same pipeline as
generate_assets2/3). Square portrait crops, transparent background.

    python3 scripts/generate_assets4.py           # everything
    python3 scripts/generate_assets4.py mirela    # one visitor
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assetlib import CHROMA, STYLE, finalize, generate

PORTRAIT = ("Bust portrait of a single character, shoulders up, facing "
            "slightly left, warm and characterful, centered: ")

VISITORS = {
    "caravan_mirela": "a shrewd middle-aged desert trader woman with sun-lined "
                      "skin, a terracotta-and-gold headscarf, layered bead "
                      "necklaces, and one raised skeptical eyebrow.",
    "caravan_tam": "a cheerful old peddler man with a huge gray beard, a "
                   "patched sage-green traveling cloak, a wide-brimmed hat "
                   "hung with tiny trinkets, and a knowing squint.",
    "caravan_alms": "a round, serene young monk in simple brown robes with a "
                    "rope belt, holding a small wooden collection bowl, with "
                    "a gentle but unmistakably businesslike smile.",
    "caravan_sable": "a sharp-eyed young spice runner woman with dark braided "
                     "hair, a deep green traveling hood, a satchel of colorful "
                     "spice pouches across her chest, and a sly half-smile.",
    "caravan_vex": "a tiny ancient grandmother with a walking cane, a black "
                   "shawl over cream linens, enormous spectacles, and the "
                   "expression of someone who has never once lost a "
                   "negotiation.",
}


def gen(slot_suffix, prompt):
    slot = f"npc/{slot_suffix}"
    full = STYLE + " " + PORTRAIT + prompt + " " + CHROMA
    raw = generate(full, slot.replace("/", "_"), aspect="1:1", size="1K")
    finalize(raw, slot, 256, 256, transparent=True, tolerance=130,
             pocket_tolerance=150, margin=0.02)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for suffix, prompt in VISITORS.items():
        if only and only not in suffix:
            continue
        print(f"→ {suffix}")
        gen(suffix, prompt)
    print("done")

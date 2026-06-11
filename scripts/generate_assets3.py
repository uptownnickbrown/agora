#!/usr/bin/env python3
"""UI icon family: replaces every emoji-as-icon in the app chrome with painted
storybook icons (user rule: no emojis as iconography). Same pipeline as
generate_assets.py / generate_assets2.py.

    python3 scripts/generate_assets3.py            # everything
    python3 scripts/generate_assets3.py icon_scale # one slot suffix
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assetlib import CHROMA, STYLE, finalize, generate

ICON = ("Flat storybook game icon, centered, no scene, no ground, no shadow, "
        "no border, no text: ")


def gen(slot, prompt, w=256, h=256, *, size="1K", tol=130, pocket=150,
        margin=0.04):
    full = STYLE + " " + ICON + prompt + " " + CHROMA
    raw = generate(full, slot.replace("/", "_"), aspect="1:1", size=size)
    finalize(raw, slot, w, h, transparent=True, tolerance=tol,
             pocket_tolerance=pocket, margin=margin)


ICONS = {
    "icon_scale": "a small brass balance scale with two hanging pans, "
                  "perfectly balanced, warm gold metal with a walnut base.",
    "icon_tax": "a small rolled parchment decree with a deep red wax seal "
                "and a thin terracotta ribbon.",
    "icon_subsidy": "a small open burlap sack brimming with gold coins, "
                    "tied loosely with a sage-green ribbon.",
    "icon_smog": "a small stone chimney stack releasing a soft curl of "
                 "gray smoke.",
    "icon_flask": "a small round alchemist's glass flask with pale green "
                  "liquid and a cork stopper.",
    "icon_mask": "a small theater mask, warm cream ceramic with a gentle "
                 "smile and terracotta ribbon ties.",
    "icon_eye": "a small ornate watching eye emblem, almond-shaped with a "
                "warm brown iris, framed by fine gold scrollwork.",
    "icon_camel": "a small cheerful camel laden with colorful bundles and "
                  "rolled carpets, standing in profile.",
    "icon_book": "a small closed storybook with a warm brown leather cover, "
                 "gilt page edges and a sage-green ribbon bookmark.",
    "icon_medal": "a small gold medal on a short terracotta-and-cream "
                  "striped ribbon.",
    "icon_medal_gold": "a small round gold first-place medallion with a "
                       "laurel ring stamped into the face.",
    "icon_medal_silver": "a small round silver second-place medallion with "
                         "a laurel ring stamped into the face.",
    "icon_medal_bronze": "a small round bronze third-place medallion with "
                         "a laurel ring stamped into the face.",
    "icon_flame": "a small warm candle flame, gold heart with a soft "
                  "terracotta edge.",
    "icon_star": "a small five-pointed gold star with softly rounded "
                 "points, hand-painted.",
    "icon_trophy": "a small gilded trophy cup with two curved handles on a "
                   "small walnut base.",
    "icon_mallet": "a small woodworker's mallet and chisel crossed in an X, "
                   "warm wood and steel.",
    "icon_windmill": "a small stone windmill with cream canvas sails and a "
                     "terracotta roof.",
    "icon_finery": "a small gilded hand mirror with a peacock feather "
                   "resting across it.",
    "icon_license": "a small unrolled parchment charter with a gold wax "
                    "seal at its foot.",
    "icon_basket": "a small woven wicker gathering basket holding sheaves "
                   "of grain and green herbs.",
    "icon_shield": "a small rounded heater shield in cream and sage-green "
                   "halves with a thin gold border.",
    "icon_globe": "a small antique desk globe on a brass stand, parchment "
                  "continents on a sage sea.",
    "icon_handshake": "two clasped hands in a firm merchant's handshake, "
                      "one in a sage-green sleeve and one in terracotta.",
    "icon_lifering": "a small cream-and-terracotta striped rope life ring.",
    "icon_banner": "a small heraldic pennant banner in sage green and cream "
                   "halves, hanging from a short wooden crossbar.",
}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, prompt in ICONS.items():
        if only and only != name:
            continue
        gen(f"ui/{name}", prompt)


if __name__ == "__main__":
    main()

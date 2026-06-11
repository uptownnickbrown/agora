#!/usr/bin/env python3
"""Regenerate the full Agora art set with Gemini (gemini-3-pro-image).

Needs GEMINI_API_KEY in the repo-root .env. Costs real money per image —
prefer re-running single families (python3 scripts/generate_assets.py pip).

Generation order matters for consistency:
  1. pip_idle is generated first and becomes the character reference for
     every other Pip pose.
  2. goods/grain is the style anchor referenced by every other small icon
     (goods, places, cosmetics).
  3. trophies chain off their own first plaque so the mounted-fish set shares
     one plaque design.
Raw renders land in scripts/raw/ (gitignored); finished PNGs land in
frontend/public/assets/ at the sizes from docs/ASSET_WISHLIST.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import assetlib
from assetlib import CHROMA, RAW_DIR, STYLE, finalize, generate

ICON = ("Flat storybook game icon of a single subject, centered, bold enough "
        "to read at thumbnail size, no scene, no ground, no shadow at all. ")
ANCHOR = ("The attached image shows the exact icon style for this game's icon "
          "set. Match its line weight, watercolor rendering, framing and "
          "scale. ")
GREEN_CHROMA = (
    "The entire background must be one single flat, uniform, solid bright "
    "green color #00FF00 with no gradient, no vignette, no texture and no "
    "shadows cast onto it. Do not use bright green or lime colors anywhere "
    "in the subject itself. The subject must not touch the edges of the image."
)


def gen(slot, prompt, w, h, *, aspect="1:1", size="2K", refs=(), tol=130,
        pocket=150, margin=0.04, scrub=None, transparent=True, chroma=CHROMA):
    name = slot.replace("/", "_")
    full = STYLE + " " + prompt + ((" " + chroma) if transparent else "")
    raw = generate(full, name, aspect=aspect, size=size, references=refs)
    finalize(raw, slot, w, h, transparent=transparent, tolerance=tol,
             pocket_tolerance=pocket, margin=margin, scrub=scrub,
             chroma_rgb=(0, 255, 0) if chroma is GREEN_CHROMA else (255, 0, 255))


def family_pip():
    gen("pip/pip_idle",
        "Character portrait of Professor Pip: a plump, endearing rock pigeon "
        "(blue-gray feathers, iridescent green-purple neck sheen) dressed as "
        "a beloved old economics professor. He wears a fitted brown tweed "
        "waistcoat with small brass buttons over a crisp white wing collar, "
        "and a gold-rimmed monocle on a fine chain over his left eye. He "
        "perches contentedly on a small rustic wooden stump, body in "
        "three-quarter view, head turned to look warmly at the viewer with "
        "bright orange eyes. Kind, scholarly, slightly smug. Full body "
        "visible including pink feet gripping the stump.",
        512, 512, tol=135, scrub=(0.0, 0.62, 0.35, 1.0))
    ref = [str(RAW_DIR / "pip_pip_idle.png")]
    base = ("The attached image is the canonical character reference for "
            "Professor Pip the pigeon. Draw the EXACT same character with "
            "identical brown tweed waistcoat with brass buttons, white wing "
            "collar, gold monocle on a chain over his left eye, same "
            "blue-gray plumage with green-purple neck sheen, same orange "
            "eyes, same proportions, same ink-and-watercolor style, in a new "
            "pose: ")
    gen("pip/pip_talking", base +
        "perched on the same wooden stump, beak open mid-lecture, one wing "
        "raised and spread like a professor making an emphatic point, eyes "
        "bright and engaged.", 512, 512, refs=ref, tol=135)
    gen("pip/pip_celebrating", base +
        "perched on the same wooden stump, both wings spread wide joyfully, "
        "head thrown back in delight, beak open in a happy cheer, a few tiny "
        "colorful paper confetti pieces floating around him (confetti in "
        "gold, terracotta and sage green only).", 512, 512, refs=ref, tol=135)
    gen("pip/pip_concerned", base +
        "perched on the same wooden stump, looking worried and concerned: "
        "monocle slightly askew and about to slip, brow feathers furrowed, "
        "beak turned down slightly, one wing raised to his cheek.",
        512, 512, refs=ref, tol=135)
    gen("pip/pip_branch", base +
        "perched calmly on a leafy oak branch that enters the composition "
        "from the right side, the branch extending toward the left, Pip "
        "sitting on it in profile facing left, a few green leaves. Wide "
        "horizontal composition with the character on the right half.",
        800, 400, aspect="16:9", refs=ref, tol=135)


GOODS = {
    "grain": "a plump tied sheaf of golden wheat, stalks bound with a simple "
             "cord, a few grains visible",
    "wood": "three split firewood logs stacked in a neat pyramid, pale cut "
            "ends showing growth rings, warm brown bark",
    "wool": "a fat round ball of cream-colored wool yarn with one knitting "
            "needle stuck through it diagonally",
    "fish": "a single plump river fish with silver-blue scales, seen from "
            "the side, slightly curved as if mid-flop",
    "ore": "a rough chunk of gray rock with glinting veins of copper-orange ore",
    "herbs": "a tied bundle of fresh green herbs with a few tiny white and "
             "gold flowers, bound with twine",
    "flour": "an open rolled-down cloth sack of white flour with a small "
             "wooden scoop resting in it",
    "lumber": "a neat stack of three planed smooth wooden planks",
    "cloth": "a folded bolt of sage-green woven cloth with a visible "
             "selvedge edge",
    "medicine": "a small cork-stoppered round potion bottle of amber liquid "
                "with a tiny paper label tag (blank tag, no writing)",
    "iron": "two heavy dark slate-gray cast iron metal ingots stacked "
            "crosswise, trapezoid ingot shape, cool gray metal with a subtle "
            "metallic sheen and darker ink shading. The metal is "
            "unmistakably gray iron, not green, not wood",
    "bread": "a crusty round loaf of bread with scored top, one wedge cut "
             "out and leaning against it",
    "garments": "a fine terracotta-colored tunic with cream trim on a simple "
                "wooden hanger",
    "tapestries": "a small hanging wall tapestry on a wooden rod, woven with "
                  "a geometric diamond motif in terracotta, gold and forest "
                  "green",
    "tools": "a crossed hammer and chisel with warm leather-wrapped grips",
    "glowdye": "a small clear glass vial of luminous bright teal dye with a "
               "cork stopper. The liquid glows from within the glass with "
               "bright teal light and small sparkles INSIDE the liquid only. "
               "Absolutely no glow, halo, aura or light effect outside the "
               "glass silhouette — the outside edge of the vial is a crisp "
               "clean ink line",
}


def family_goods():
    gen("goods/grain", ICON + "The subject: " + GOODS["grain"] + ".",
        256, 256, size="1K", scrub=(0.0, 0.75, 1.0, 1.0))
    ref = [str(RAW_DIR / "goods_grain.png")]
    for k, v in GOODS.items():
        if k == "grain":
            continue
        gen(f"goods/{k}", ANCHOR + ICON + "The subject: " + v + ".",
            256, 256, size="1K", refs=ref, scrub=(0.0, 0.78, 1.0, 1.0))


PLACES = {
    "market": "a small wooden market stall with a terracotta-and-cream "
              "striped awning, a brass balance scale on the counter, two "
              "simple Greek columns rising behind it",
    "shop": "a cozy storefront facade with a hanging gilt sign (blank face), "
            "a bottle-glass bay window with jars and goods on display, warm "
            "wooden door",
    "workshop": "a sturdy wooden workbench with a hammer and a loom shuttle "
                "on top and two plump sacks of grain leaning against its legs",
    "docks": "a short wooden pier post and deck corner with a small moored "
             "rowboat and a coiled rope on the planks, a hint of calm water "
             "beneath",
    "puzzle": "an open leather-bound ledger book with a white quill pen "
              "resting on it and a brass magnifying glass lying over one "
              "page, the pages show faint ruled columns (no readable text or "
              "numbers)",
    "crier": "a polished brass posting horn with a red cord and tassel "
             "resting across a rolled broadsheet newspaper tied with string "
             "(no readable text)",
    "guild": "a grand arched wooden double door with iron hinges and an iron "
             "door knocker shaped like a sheaf of wheat",
    "boards": "a green laurel wreath encircling a small golden trophy cup",
}


def family_places():
    ref = [str(RAW_DIR / "goods_grain.png")]
    for k, v in PLACES.items():
        gen(f"places/{k}", ANCHOR + ICON + "The subject: " + v + ".",
            256, 256, size="1K", refs=ref, scrub=(0.0, 0.78, 1.0, 1.0))
    gen("places/docks_scene",
        "A wide cozy scene of a small fishing dock in a pre-industrial "
        "market town: a wooden pier reaching into calm green-blue water from "
        "the left, a moored rowboat, coiled ropes and a lantern post, "
        "red-roofed whitewashed cottages and gentle hills behind, warm "
        "morning light, a few gulls. Painted as a full scene with the cream "
        "parchment sky.", 480, 280, aspect="16:9", transparent=False)


def family_brand():
    gen("brand/agora_crest",
        "A game crest emblem in shield-badge composition: a classical Greek "
        "temple front with four columns, with small cream-and-terracotta "
        "market awnings stretched between the columns, all framed within a "
        "wreath of golden wheat stalks that curves around the sides and "
        "meets at the bottom with a small gold ribbon. Balanced, iconic, "
        "centered, flat storybook emblem style, no scene, no shadow.",
        512, 512, pocket=185)
    gen("brand/agora_hero",
        "A wide painted panoramic view of a lightly fantastical "
        "pre-industrial Mediterranean market town in warm morning light: a "
        "bustling agora square with market stalls under striped awnings in "
        "the foreground, a classical temple with columns rising behind them, "
        "red-roofed whitewashed houses climbing gentle green hills, olive "
        "trees, a few pigeons in the sky. Soft golden light, inviting and "
        "cozy, painted edge-to-edge.",
        1600, 600, aspect="21:9", size="4K", transparent=False)
    compose_pwa_icons()


def compose_pwa_icons():
    from PIL import Image, ImageDraw

    crest = Image.open(assetlib.OUT_DIR / "brand/agora_crest.png")
    for size in (192, 512):
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5,
                            fill=(45, 74, 58, 255))
        inner = int(size * 0.78)
        canvas.alpha_composite(
            crest.resize((inner, inner), Image.LANCZOS),
            ((size - inner) // 2, (size - inner) // 2))
        canvas.save(assetlib.OUT_DIR / f"brand/icon_{size}.png")


EVENT = ("A storybook event illustration scene for the game's town "
         "newspaper, painted edge to edge as a full scene with absolutely no "
         "frame, no border, no curtains and no vignette — the painting runs "
         "off all four edges. ")
EVENTS = {
    "festival": "The Lantern Festival: a night view of the market square "
        "strung with criss-crossing strings of glowing warm paper lanterns "
        "in gold and terracotta, market stalls below, a cheerful crowd as "
        "simple dark silhouettes, deep blue-green night sky, fireflies.",
    "drought": "A drought: a field of cracked dry earth with wilted golden "
        "wheat stalks drooping, a dry irrigation ditch winding through, the "
        "town's red roofs small on the horizon, and one single small hopeful "
        "white cloud in a pale dusty sky. Muted, dusty palette, gentle mood "
        "rather than grim.",
    "decree": "A royal decree: a herald in a terracotta tabard nailing a "
        "large parchment decree (blank, with a red wax seal) to the wooden "
        "market notice board, a small crowd of townsfolk with arms raised in "
        "animated reaction, market awnings behind.",
    "gray_skies": "Early industry arrives: the town skyline where the sky is "
        "split down the middle — clean cream sky with white clouds on the "
        "left half, gray smoggy haze on the right half drifting from two "
        "brick smokestacks among the red roofs. Gentle, not apocalyptic.",
    "fishery_collapse": "The fishery struggles: the wooden dock with two "
        "fishermen holding up completely empty nets, one single tiny fish "
        "flopping on the planks between them, a dismayed seagull watching. "
        "Gentle humor, not grim, calm green-blue water.",
    "market_wars": "A price war: two rival market stalls facing off across "
        "the square aisle, one with terracotta striped awning and one with "
        "sage green striped awning, colorful bunting strung everywhere "
        "overhead, each stall with a large dramatic blank wooden price sign, "
        "the two merchants glaring at each other, goods piled high.",
    "auction": "A sealed-bid royal auction: a royal clerk in formal green "
        "robes standing behind a small wooden table with an ornate locked "
        "ballot box with a coin slot, a queue of hopeful merchants each "
        "clutching folded paper bids, inside a market hall with columns.",
}


def family_events():
    gen("crier/masthead",
        "An engraved-style newspaper masthead ornament in antique woodcut "
        "style with the game's warm watercolor tinting: at the center a "
        "proud heraldic pigeon with spread wings holding a brass posting "
        "horn, flanked symmetrically on both sides by elegant scrollwork "
        "flourishes, wheat stalks and ribbon swirls that extend "
        "horizontally. Wide horizontal ornament, no frame border, no text or "
        "lettering anywhere.", 600, 160, aspect="21:9", pocket=185)
    for k, v in EVENTS.items():
        gen(f"events/{k}", EVENT + v, 600, 340, aspect="16:9",
            transparent=False)


def family_trophies():
    gen("trophies/old_whiskerjaw", ICON +
        "The subject: a mounted fishing trophy — a grizzled old gray-green "
        "catfish with magnificent long drooping whiskers, battle-scarred "
        "fins and a weary, wise expression, mounted on a varnished dark-wood "
        "wall plaque shaped like a shield with a small blank brass "
        "nameplate.", 256, 256, size="1K", pocket=160)
    ref = [str(RAW_DIR / "trophies_old_whiskerjaw.png")]
    chain = ("The attached image is a mounted fishing trophy from this game. "
             "Draw a NEW trophy in the exact same style, with the SAME "
             "varnished dark-wood shield-shaped wall plaque and small blank "
             "brass nameplate, same framing and scale, but with a different "
             "fish: ")
    gen("trophies/smug_trout", chain +
        "a plump rainbow trout with an insufferably self-satisfied smug "
        "grin, half-lidded eyes and a raised eyebrow. " + ICON,
        256, 256, size="1K", refs=ref, pocket=160)
    gen("trophies/gilded_leviathan", chain +
        "an absurdly large, magnificent leviathan fish sculpted entirely "
        "from gleaming polished GOLD — every scale, fin and whisker is shiny "
        "metallic gold like a gilded statue, with warm golden highlights and "
        "a haughty triumphant expression. " + ICON,
        256, 256, size="1K", refs=ref, pocket=160)


COSMETICS = {
    "hat_wayfarer": "a weathered wide-brimmed leather traveler's hat with a "
        "small terracotta band and a single jaunty pheasant feather tucked "
        "in it",
    "rod_gilded": "an elegant fishing rod of dark polished wood covered in "
        "fine gold filigree scrollwork, with a brass reel and a thin line "
        "ending in a small hook",
    "quill_sage": "a wise-looking tall white goose quill with a subtle "
        "sage-green tip, standing in a small round polished brass inkstand",
    "awning_striped": "a crisp shop awning with bold terracotta-and-cream "
        "stripes and a gently scalloped front edge, on a simple wooden frame "
        "seen straight on",
    "sign_gilt": "a hanging shop sign: an ornate gilt wooden sign board with "
        "a blank face, hanging by two small brass chains from a decorative "
        "wrought-iron bracket",
    "fountain_small": "a modest two-tier round stone courtyard fountain with "
        "water gently overflowing the small upper basin into the wide lower "
        "basin",
    "peacock": "a live peacock standing in profile looking expensive and "
        "unimpressed, long elegant train of teal-and-gold eye feathers "
        "trailing behind, head turned slightly away in disdain",
}


def family_cosmetics():
    ref = [str(RAW_DIR / "goods_grain.png")]
    for k, v in COSMETICS.items():
        gen(f"cosmetics/{k}", ANCHOR + ICON + "The subject: " + v + ".",
            256, 256, size="1K", refs=ref, scrub=(0.0, 0.8, 1.0, 1.0))
    # The royal cloak is deep purple, so it keys against green, not magenta.
    gen("cosmetics/cloak_royal", ANCHOR + ICON +
        "The subject: a regal deep-purple velvet cloak with white ermine "
        "trim flecked with black, fastened by a round clasp holding a small "
        "glowing teal gem, displayed draped on a simple wooden stand.",
        256, 256, size="1K", refs=ref, chroma=GREEN_CHROMA)


def family_ui():
    import numpy as np
    from PIL import Image
    from scipy import ndimage

    style_min = ("Hand-drawn ink and warm watercolor board-game UI element, "
                 "cozy storybook style, no text anywhere. Show ONLY one "
                 "single object floating on the flat magenta background with "
                 "absolutely nothing else around it — no scene, no market, "
                 "no props, no characters: ")
    raw = generate(STYLE +
        " A blank sheet of aged cream parchment paper #F6EFDD filling almost "
        "the whole frame, with softly torn deckled edges all around, subtle "
        "fiber texture and very gentle warm staining toward the edges. "
        "Completely blank surface, no writing, no drawings. Flat, viewed "
        "perfectly straight on. " + CHROMA,
        "ui_parchment_panel", aspect="4:3")
    img = assetlib.key_out_background(Image.open(raw), tolerance=160,
                                      pocket_tolerance=150)
    img = assetlib.scrub_magenta(img, (0.0, 0.0, 1.0, 1.0))
    a = np.array(img)
    mask = ndimage.binary_erosion(a[..., 3] > 128, iterations=4)
    a[..., 3] = np.where(mask, a[..., 3], 0)
    assetlib.trim_and_fit(Image.fromarray(a), 800, 600, margin=0.01).save(
        assetlib.OUT_DIR / "ui/parchment_panel.png")

    gen("ui/wood_plaque", style_min +
        "a horizontal rectangular wooden plaque of warm brown carved wood "
        "with a neat beveled carved border and visible wood grain, "
        "completely blank face, viewed perfectly straight on, wide and "
        "short.", 400, 120, aspect="21:9", tol=140, margin=0.01)
    gen("ui/banner_scroll", style_min +
        "a wide horizontal unrolled parchment scroll banner with gently "
        "curled ends, one round iron nail head at each end, completely "
        "blank cream face, viewed straight on, wide and short.",
        500, 140, aspect="21:9", tol=140, margin=0.01)
    gen("ui/coin", ICON +
        "The subject: a single round gold coin seen perfectly face-on, "
        "stamped with a tied sheaf of wheat in relief, slightly irregular "
        "hand-struck edge, warm muted gold.", 128, 128, size="1K")
    gen("ui/effort_token", ICON +
        "The subject: a single round sage-green stamina token seen perfectly "
        "face-on, like a smooth clay or wooden game piece with a simple leaf "
        "embossed in relief, slightly irregular hand-made edge.",
        128, 128, size="1K")
    make_felt()


def make_felt():
    """The felt is procedural: generated felt kept sprouting illustrations,
    and synthesis guarantees a perfectly tileable, on-palette texture."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage

    rng = np.random.default_rng(7)
    base = np.array([45, 74, 58], float)
    k = np.outer(np.hanning(31), np.hanning(31))
    k /= k.sum()
    sm = ndimage.convolve(rng.normal(0, 1, (512, 512)), k, mode="wrap")
    fib = ndimage.convolve(rng.normal(0, 1, (512, 512)),
                           np.ones((1, 5)) / 5, mode="wrap")
    tex = (base[None, None, :] + sm[..., None] * 22 + fib[..., None] * 5
           + rng.normal(0, 2.2, (512, 512, 1)))
    Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8)).save(
        assetlib.OUT_DIR / "ui/felt_texture.png")


FAMILIES = {
    "pip": family_pip,
    "goods": family_goods,
    "places": family_places,
    "brand": family_brand,
    "events": family_events,
    "trophies": family_trophies,
    "cosmetics": family_cosmetics,
    "ui": family_ui,
}

if __name__ == "__main__":
    picks = sys.argv[1:] or list(FAMILIES)
    for p in picks:
        print(f"=== {p} ===")
        FAMILIES[p]()

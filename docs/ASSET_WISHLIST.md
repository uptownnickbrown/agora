# Assets I Wish I Had

> **Status: all slots below are filled.** Every asset was generated with
> Gemini (`gemini-3-pro-image`) — see `scripts/generate_assets.py` for the
> full reproducible prompt set and `scripts/assetlib.py` for the
> chroma-key/crop pipeline. Re-run a single family with e.g.
> `python3 scripts/generate_assets.py pip` (needs `GEMINI_API_KEY` in `.env`).

The frontend ships with an `Asset` component (`frontend/src/ui.tsx`) that loads
`frontend/public/assets/<slot>.png` and **gracefully falls back to an emoji
glyph** when the file is missing. Every slot below is therefore already wired —
drop a rendered PNG at the listed path and it appears in the UI with zero code
changes.

## Style guide (prepend to every generation prompt)

> Storybook illustration for a cozy economics game set in a lightly fantastical
> pre-industrial market town. Hand-drawn ink linework with warm watercolor
> fills. Palette: cream parchment (#F6EFDD), deep forest green (#2D4A3A), warm
> wood brown (#8A6A48), terracotta (#C4633E), sage green (#7A9460), muted gold
> (#D9A93F). Soft shadows, slightly imperfect lines, gentle humor. No text in
> the image. Transparent background unless noted. Consistent with a
> Splendor/Catan-quality board game.

The two reference mockups from the designer are the canonical look: parchment
panels on a deep-green felt tabletop, wooden plaques, and Professor Pip the
pigeon (monocle, brown waistcoat, white collar).

## 1. Professor Pip (highest priority — he IS the brand)

| Slot (path under `public/assets/`) | Size | Description |
|---|---|---|
| `pip/pip_idle.png` | 512×512 | Professor Pip, a plump rock pigeon in a brown tweed waistcoat with a white collar and a gold monocle on his left eye, perched contentedly on a wooden stump, 3/4 view, looking at the viewer. The mockups' pigeon, exactly. |
| `pip/pip_talking.png` | 512×512 | Same pigeon, beak open mid-lecture, one wing raised like a professor making a point. |
| `pip/pip_celebrating.png` | 512×512 | Same pigeon, wings spread joyfully, tiny confetti around him. Shown when a student aces a check. |
| `pip/pip_concerned.png` | 512×512 | Same pigeon, monocle slightly askew, brow feathers furrowed. Shown with wrong answers and bankruptcies. |
| `pip/pip_branch.png` | 800×400 | Pip perched on a leafy branch entering from the right, parchment-friendly composition (used beside speech bubbles, as in mockup 1). |

**Consistency matters more than anything for Pip** — generate the idle pose
first, then feed it back as a reference image for the other poses.

## 2. Place tiles (navigation, shown ~80×80, render 256×256)

| Slot | Description |
|---|---|
| `places/market.png` | A wooden market stall with a striped awning, scales on the counter, Greek-ish columns behind. |
| `places/shop.png` | A cozy storefront with a hanging gilt sign, bottle-glass window, goods in the window. |
| `places/workshop.png` | A workbench with hammer, loom shuttle, and sacks of grain leaning against it. |
| `places/docks.png` | A short wooden pier with a moored rowboat and a coiled rope, calm water. |
| `places/puzzle.png` | An open leather ledger with a quill and a magnifying glass over a column of figures. |
| `places/crier.png` | A brass posting horn over a rolled broadsheet newspaper. |
| `places/guild.png` | A grand wooden door with an iron knocker shaped like a sheaf of wheat. |
| `places/boards.png` | A laurel wreath around a small golden cup. |
| `places/docks_scene.png` (480×280) | Wider dock scene for the fishing screen: the pier from mockup 2, fisherman silhouette optional, red-roofed cottages behind. |

## 3. Goods icons (shown 22–32px inline, render 256×256, transparent bg)

One per good, simple and readable at thumbnail size — these are the most-seen
art in the game (inventory, order book, market list, recipes):

`goods/grain.png` (a tied sheaf of golden wheat) · `goods/wood.png` (three
stacked split logs) · `goods/wool.png` (a fat ball of cream yarn with a knitting
needle) · `goods/fish.png` (a plump silver-blue river fish) · `goods/ore.png`
(a chunk of gray rock with copper glints) · `goods/herbs.png` (a tied bundle of
green herbs with tiny flowers) · `goods/flour.png` (an open cloth sack of white
flour, scoop inside) · `goods/lumber.png` (neat planed planks) ·
`goods/cloth.png` (a folded bolt of sage-green cloth) · `goods/medicine.png`
(a small cork-stoppered potion bottle, amber liquid) · `goods/iron.png` (two
gray ingots) · `goods/bread.png` (a crusty round loaf, one wedge cut) ·
`goods/garments.png` (a fine terracotta tunic on a wooden hanger) ·
`goods/tapestries.png` (a small hanging tapestry with a geometric diamond motif,
as in mockup 2's pattern designer) · `goods/tools.png` (crossed hammer and
chisel with leather grips) · `goods/glowdye.png` (a glass vial of luminous
teal dye, faint glow — the one magical-feeling good).

## 4. Brand & PWA

| Slot | Size | Description |
|---|---|---|
| `brand/agora_crest.png` | 512×512 | The game's crest: a classical temple front with market awnings between the columns, wreathed in wheat, "shield badge" composition. Login screen + favicon source. |
| `brand/icon_192.png`, `brand/icon_512.png` | 192/512 | The crest simplified onto a deep-green rounded square (PWA home-screen icons — referenced by `manifest.json`). |
| `brand/agora_hero.png` | 1600×600 | Wide painted view of the market town from mockup 1's header: stalls, temple, hills, warm morning light. Login/landing backdrop. (Opaque.) |

## 5. The Crier & events

| Slot | Size | Description |
|---|---|---|
| `crier/masthead.png` | 600×160 | An engraved-style newspaper masthead ornament: a heraldic pigeon with a posting horn, flourishes either side. |
| `events/festival.png` | 600×340 | The Lantern Festival: strings of glowing paper lanterns over the night market square, crowds as simple silhouettes. |
| `events/drought.png` | 600×340 | Cracked earth field, wilted wheat, a single hopeful cloud. Muted palette. |
| `events/decree.png` | 600×340 | A royal herald nailing a parchment decree to the market board, onlookers' arms raised. |
| `events/gray_skies.png` | 600×340 | The town skyline with smokestacks, the sky split: clean left, smoggy gray right. |
| `events/fishery_collapse.png` | 600×340 | The dock with empty nets, one tiny fish, a dismayed fisherman. Gentle, not grim. |
| `events/market_wars.png` | 600×340 | Two market stalls facing off across the square, bunting everywhere, dramatic price signs (blank). |
| `events/auction.png` | 600×340 | A royal clerk with a sealed-bid box, merchants queueing with folded papers. |

## 6. Trophies, achievements & cosmetics (shown small, render 256×256)

| Slot | Description |
|---|---|
| `trophies/gilded_leviathan.png` | An absurdly large ornate golden fish mounted on a plaque. |
| `trophies/old_whiskerjaw.png` | A grizzled catfish with magnificent whiskers, mounted. |
| `trophies/smug_trout.png` | A trout with an insufferably self-satisfied expression, mounted. |
| `cosmetics/hat_wayfarer.png` | A weathered wide-brim traveler's hat with a feather. |
| `cosmetics/rod_gilded.png` | A gold-filigreed fishing rod. |
| `cosmetics/cloak_royal.png` | A deep-purple cloak with ermine trim and a glowdye-blue clasp. |
| `cosmetics/quill_sage.png` | A wise-looking white quill in a brass stand. |
| `cosmetics/awning_striped.png` | A crisp terracotta-and-cream striped shop awning. |
| `cosmetics/sign_gilt.png` | A hanging gilt shop sign (blank face). |
| `cosmetics/fountain_small.png` | A modest two-tier stone courtyard fountain. |
| `cosmetics/peacock.png` | A live peacock looking expensive and unimpressed. |

## 7. UI furniture (lower priority — CSS approximates these today)

| Slot | Size | Description |
|---|---|---|
| `ui/parchment_panel.png` | 800×600, 9-slice friendly | A parchment sheet with softly torn edges and a faint fiber texture (replaces the CSS `.panel`). |
| `ui/wood_plaque.png` | 400×120, 9-slice | The wooden plaque from the mockups' "Effort Points" box, with carved bevel. |
| `ui/banner_scroll.png` | 500×140 | The hanging title scroll with two nail heads (replaces CSS `.banner`). |
| `ui/coin.png` | 128×128 | A single gold copper with a wheat-sheaf stamp. |
| `ui/effort_token.png` | 128×128 | A sage-green stamina token with a leaf emboss. |
| `ui/felt_texture.png` | 512×512, tileable | The deep-green felt tabletop with subtle fiber noise. |

## Caravan visitors (the haggling minigame) — DONE 2026-07-02

Bust portraits, 256×256, transparent. Generated by `scripts/generate_assets4.py`.

| Slot | Description |
|---|---|
| `npc/caravan_mirela.png` | Mirela of the Dune Caravan — shrewd desert trader, skeptical eyebrow. |
| `npc/caravan_tam.png` | Old Tam the Peddler — huge gray beard, trinket-hung hat. |
| `npc/caravan_alms.png` | Brother Alms of the Abbey — serene monk, businesslike smile. |
| `npc/caravan_sable.png` | Sable the Spice Runner — hooded, satchel of spice pouches. |
| `npc/caravan_vex.png` | Grandmother Vex — enormous spectacles, has never lost a negotiation. |

## Generation workflow suggestion

1. Generate **Pip idle** until he matches the mockups; lock him as the reference.
2. Batch the 16 goods icons (consistency prompt: "same style as previous, flat
   storybook icon, centered, transparent background").
3. Place tiles, then brand, then events; UI furniture last (CSS already does a
   passable job there).
4. Drop files into `frontend/public/assets/<slot>.png` — no code changes needed.
5. Anything rendered at the wrong aspect: the UI uses `object-fit: contain`, so
   over-cropping is safer than over-padding.

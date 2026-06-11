"""Shared helpers for the Agora asset-generation pipeline.

Generates art with Gemini (gemini-3-pro-image), removes chroma-key
backgrounds with a border-connected flood mask, and normalizes output to the
sizes in docs/ASSET_WISHLIST.md. Raw model output is kept in scripts/raw/ so
any asset can be re-cropped without re-spending on generation.
"""

import io
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "scripts" / "raw"
OUT_DIR = ROOT / "frontend" / "public" / "assets"
MODEL = "gemini-3-pro-image"

STYLE = (
    "Storybook illustration for a cozy economics game set in a lightly "
    "fantastical pre-industrial market town. Hand-drawn ink linework with warm "
    "watercolor fills. Palette: cream parchment #F6EFDD, deep forest green "
    "#2D4A3A, warm wood brown #8A6A48, terracotta #C4633E, sage green #7A9460, "
    "muted gold #D9A93F. Soft shadows, slightly imperfect lines, gentle humor. "
    "Absolutely no text, letters, numbers, or watermarks anywhere in the image. "
    "Consistent with a Splendor or Catan quality board game."
)

CHROMA = (
    "The entire background must be one single flat, uniform, solid bright "
    "magenta color #FF00FF with no gradient, no vignette, no texture and no "
    "shadows cast onto it. Do not use pink, magenta or purple anywhere in the "
    "subject itself. The subject must not touch the edges of the image."
)


def _client():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


_CLIENT = None


def generate(prompt, name, aspect="1:1", size="2K", references=(), retries=3):
    """Generate one image, save raw PNG to scripts/raw/<name>.png, return path."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _client()
    from google.genai import types

    parts = []
    for ref in references:
        parts.append(
            types.Part.from_bytes(data=Path(ref).read_bytes(), mime_type="image/png")
        )
    parts.append(types.Part.from_text(text=prompt))

    cfg = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect, image_size=size),
    )

    raw_path = RAW_DIR / f"{name}.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(retries):
        try:
            resp = _CLIENT.models.generate_content(
                model=MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=cfg,
            )
            for part in resp.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img = Image.open(io.BytesIO(part.inline_data.data))
                    img.save(raw_path)
                    print(f"  raw {name}: {img.size[0]}x{img.size[1]}")
                    return raw_path
            last_err = RuntimeError(f"no image part in response for {name}")
        except Exception as e:  # noqa: BLE001 - report and retry transient API errors
            last_err = e
        wait = 2 ** (attempt + 1)
        print(f"  retry {name} in {wait}s: {last_err}")
        time.sleep(wait)
    raise RuntimeError(f"generation failed for {name}: {last_err}")


def key_out_background(img, tolerance=110, despill=True, pocket_tolerance=70,
                       chroma_rgb=(255, 0, 255)):
    """Make the magenta backdrop transparent.

    Only pixels color-close to magenta AND flood-connected to the image border
    become transparent, so magenta-ish colors inside the subject survive.
    """
    rgba = np.array(img.convert("RGBA"), dtype=np.float32)
    r, g, b = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    cr, cg, cb = chroma_rgb
    dist = np.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
    near = dist < tolerance

    labels, _ = ndimage.label(near)
    border = np.unique(
        np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    )
    border = border[border != 0]
    # Border-connected backdrop, plus any enclosed pocket of backdrop showing
    # through gaps in the subject (those are unmistakably magenta).
    bg = np.isin(labels, border) | (dist < pocket_tolerance)

    alpha = rgba[..., 3]
    alpha[bg] = 0.0
    # Feather: partially fade pixels just outside the keyed tolerance that sit
    # against the background, to soften watercolor edges.
    edge_zone = ndimage.binary_dilation(bg, iterations=2) & ~bg
    soft = edge_zone & (dist < tolerance + 60)
    fade = np.clip((dist - tolerance) / 60.0, 0.0, 1.0)
    alpha[soft] = alpha[soft] * fade[soft]

    if despill and chroma_rgb == (255, 0, 255):
        # Pull magenta fringes toward neutral, but only in the thin band of
        # subject pixels right against the keyed background and only where the
        # color is genuinely magenta-ish, so warm browns stay warm.
        band = ndimage.binary_dilation(bg, iterations=3) & ~bg
        spill = band & (dist < tolerance + 90)
        excess = np.clip(((r + b) / 2.0 - g) * 0.6, 0.0, None)
        r[spill] = np.clip(r[spill] - excess[spill], 0, 255)
        b[spill] = np.clip(b[spill] - excess[spill], 0, 255)

    rgba[..., 3] = alpha
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def scrub_magenta(img, box):
    """Erase saturated-magenta pixels inside box=(x0, y0, x1, y1) as fractions
    of width/height — for stray keyed-backdrop shadows the flood fill missed."""
    rgba = np.array(img.convert("RGBA"), dtype=np.float32)
    h, w = rgba.shape[:2]
    x0, y0, x1, y1 = (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))
    region = rgba[y0:y1, x0:x1]
    r, g, b = region[..., 0], region[..., 1], region[..., 2]
    hit = (r - g > 40) & (b - g > 30)
    region[..., 3][hit] = 0
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def trim_and_fit(img, target_w, target_h, margin=0.04):
    """Crop transparent padding to content, then letterbox-fit onto a
    transparent canvas of the target size with a small margin."""
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    inner_w = int(target_w * (1 - 2 * margin))
    inner_h = int(target_h * (1 - 2 * margin))
    scale = min(inner_w / img.width, inner_h / img.height)
    img = img.resize(
        (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    canvas.paste(img, ((target_w - img.width) // 2, (target_h - img.height) // 2))
    return canvas


def cover_crop(img, target_w, target_h):
    """Scale to cover the target box, center-crop the overflow (opaque art)."""
    scale = max(target_w / img.width, target_h / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    x = (img.width - target_w) // 2
    y = (img.height - target_h) // 2
    return img.crop((x, y, x + target_w, y + target_h)).convert("RGB")


def finalize(raw_path, slot, target_w, target_h, transparent=True, tolerance=110,
             margin=0.04, scrub=None, pocket_tolerance=70,
             chroma_rgb=(255, 0, 255)):
    """Process a raw render into frontend/public/assets/<slot>.png."""
    out = OUT_DIR / f"{slot}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(raw_path)
    if transparent:
        img = key_out_background(img, tolerance=tolerance,
                                 pocket_tolerance=pocket_tolerance,
                                 chroma_rgb=chroma_rgb)
        if scrub:
            img = scrub_magenta(img, scrub)
        img = trim_and_fit(img, target_w, target_h, margin=margin)
        img.save(out)
    else:
        cover_crop(img, target_w, target_h).save(out)
    print(f"  -> {out.relative_to(ROOT)} ({target_w}x{target_h})")
    return out


def run(spec_list):
    """spec: dict(slot, prompt, w, h, aspect='1:1', transparent=True,
    references=(), size='2K', tolerance=110, margin=0.04, chroma=True)."""
    for spec in spec_list:
        name = spec["slot"].replace("/", "_")
        prompt = STYLE + " " + spec["prompt"]
        if spec.get("transparent", True) and spec.get("chroma", True):
            prompt += " " + CHROMA
        raw = generate(
            prompt,
            name,
            aspect=spec.get("aspect", "1:1"),
            size=spec.get("size", "2K"),
            references=spec.get("references", ()),
        )
        finalize(
            raw,
            spec["slot"],
            spec["w"],
            spec["h"],
            transparent=spec.get("transparent", True),
            tolerance=spec.get("tolerance", 110),
            margin=spec.get("margin", 0.04),
            scrub=spec.get("scrub"),
        )


if __name__ == "__main__":
    print("import this module from a generation script", file=sys.stderr)

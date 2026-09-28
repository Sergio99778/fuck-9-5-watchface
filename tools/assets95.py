"""Renders the spray-paint bitmaps for the 9-5 face.

Everything is painted in (near) white with texture in the alpha channel, so the watch face can
tint it with the chosen spray colour. Positions/sizes are written to assets.json for design95.py.
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DRAWABLE = os.path.join(PROJECT, "src", "res", "drawable-nodpi")
SYMBOLS = os.environ.get(
    "SYMBOLS_FONT", "/home/claude/vendor/mdi/variablefont/MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf")
ICONS = {"ic_steps": 0xF87D, "ic_battery": 0xE1A5, "ic_battery_charging": 0xE1A3, "ic_battery_alert": 0xE19C,
         "ic_uv": 0xE81A, "ic_heart": 0xE87E}
MARKER = os.environ.get("MARKER_FONT",
                        "/home/claude/vendor/gfonts/apache/permanentmarker/PermanentMarker-Regular.ttf")

C = 225.0
RING_R = 206.0
WORK_START, WORK_END = 270.0, 510.0      # 9 o'clock -> 5 o'clock, clockwise (degrees, 0 = 12)


def _rgba_from_alpha(alpha, seed, shade_amount=0.14):
    h, w = alpha.shape
    shade = 1.0 - shade_amount * np.random.default_rng(seed).random((h, w))
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for i in range(3):
        rgba[..., i] = np.clip(255 * shade, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _spray(mask, scale, seed, halo_px=6.0, halo_alpha=0.26, speck=0.10, rough=0.25):
    """Rough-edged core + soft overspray + speckles, from a hard mask."""
    m = mask.filter(ImageFilter.GaussianBlur(1.4 * scale))
    arr = np.asarray(m, dtype=np.float32) / 255
    noise = np.random.default_rng(seed).random(arr.shape).astype(np.float32)
    core = np.clip((arr - 0.35 - rough * (noise - 0.5)) * 6, 0, 1)
    halo = np.asarray(mask.filter(ImageFilter.GaussianBlur(halo_px * scale)), dtype=np.float32) / 255
    specks = (np.random.default_rng(seed + 1).random(arr.shape) < halo * speck).astype(np.float32)
    return np.clip(core + halo * halo_alpha + specks * 0.8, 0, 1)


def _crop(img, margin):
    bbox = img.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - margin), max(0, y0 - margin), min(img.width, x1 + margin),
                     min(img.height, y1 + margin)))


def tag(text, size_units, angle, seed, scale=2, drips=6):
    rnd = random.Random(seed)
    f = ImageFont.truetype(MARKER, int(size_units * scale))
    l, t, r, b = f.getbbox(text)
    pad = int(40 * scale)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255)
    arr = np.asarray(mask, dtype=np.uint8)
    d = ImageDraw.Draw(mask)
    ink_rows = np.where(arr.max(axis=1) > 128)[0]
    base_zone = ink_rows.max() - 0.22 * (ink_rows.max() - ink_rows.min())
    lowest = np.array([np.where(arr[:, x] > 128)[0].max() if arr[:, x].max() > 128 else -1
                       for x in range(arr.shape[1])])
    cols = np.where(lowest >= base_zone)[0]
    chosen = sorted(rnd.sample(list(cols[::max(1, len(cols) // 40)]), min(drips, len(cols))))
    for x in chosen:
        ys = np.where(arr[:, x] > 128)[0]
        y0 = int(ys.max())
        length = rnd.randint(6, 26) * scale
        wd = rnd.uniform(1.8, 3.2) * scale
        d.line([x, y0 - 3 * scale, x, y0 + length], fill=255, width=int(round(wd)))
        d.ellipse([x - wd * 0.9, y0 + length - wd, x + wd * 0.9, y0 + length + wd * 1.3], fill=255)
    alpha = _spray(mask, scale, seed, halo_px=6.5, halo_alpha=0.28, speck=0.10)
    img = _rgba_from_alpha(alpha, seed + 5)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    return _crop(img, int(3 * scale))


def dab(seed, size_units=32, scale=2):
    """One burst of spray, elongated along x; placed tangent to the ring so neighbours merge."""
    rnd = random.Random(seed)
    n = int(size_units * scale)
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    c = n / 2
    for _ in range(rnd.randint(9, 12)):
        r = rnd.uniform(4.2, 6.0) * scale
        ox, oy = rnd.gauss(0, 3.0 * scale), rnd.gauss(0, 0.9 * scale)
        d.ellipse([c + ox - r, c + oy - r, c + ox + r, c + oy + r], fill=255)
    alpha = _spray(mask, scale, seed, halo_px=2.4, halo_alpha=0.35, speck=0.14, rough=0.30)
    return _rgba_from_alpha(alpha, seed + 9)


def band(width_units, scale, seed):
    """The whole 9-to-5 arc as one sprayed band, on a full 450x450 canvas at `scale`."""
    n = int(450 * scale)
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    rnd = random.Random(seed)
    steps = int((WORK_END - WORK_START) * 3)
    for i in range(steps + 1):
        a = math.radians(WORK_START + (WORK_END - WORK_START) * i / steps)
        rr = (RING_R + rnd.uniform(-1.0, 1.0)) * scale
        ww = width_units * scale * rnd.uniform(0.85, 1.1)
        x, y = C * scale + rr * math.sin(a), C * scale - rr * math.cos(a)
        d.ellipse([x - ww / 2, y - ww / 2, x + ww / 2, y + ww / 2], fill=255)
    alpha = _spray(mask, scale, seed, halo_px=4.0, halo_alpha=0.25, speck=0.08)
    return _rgba_from_alpha(alpha, seed + 3)


def track(width_units=9.0, scale=1, seed=3):
    """Dim full track, cropped to its bounding box."""
    img = band(width_units, scale, seed)
    bbox = img.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    return img.crop(bbox), (bbox[0] / scale, bbox[1] / scale)


def progress_segments(n_segments=48, width_units=12.0, scale=2, seed=4, overlap_deg=0.5):
    """Slice one bright band into wedges. Showing wedges 0..k reproduces the band from 9 o'clock
    up to the current time without seams, because the pieces all come from the same painting."""
    img = band(width_units, scale, seed)
    n = img.width
    cx = cy = C * scale
    big = n  # radius well beyond the band
    out = []
    step = (WORK_END - WORK_START) / n_segments
    for k in range(n_segments):
        a0 = WORK_START + k * step - (overlap_deg if k else 2.0)
        a1 = WORK_START + (k + 1) * step + (overlap_deg if k < n_segments - 1 else 2.0)
        pts = [(cx, cy)]
        for i in range(9):
            a = math.radians(a0 + (a1 - a0) * i / 8)
            pts.append((cx + big * math.sin(a), cy - big * math.cos(a)))
        wedge = Image.new("L", (n, n), 0)
        ImageDraw.Draw(wedge).polygon(pts, fill=255)
        piece = img.copy()
        piece.putalpha(ImageChops.multiply(img.getchannel("A"), wedge))
        x0, y0, x1, y1 = piece.getchannel("A").point(lambda v: 255 if v > 4 else 0).getbbox()
        # snap the crop to whole canvas units so the part box is exact
        x0, y0 = (x0 // scale) * scale, (y0 // scale) * scale
        x1, y1 = -(-x1 // scale) * scale, -(-y1 // scale) * scale
        out.append((piece.crop((x0, y0, x1, y1)), (x0 // scale, y0 // scale, (x1 - x0) // scale, (y1 - y0) // scale)))
    return out


def symbol(codepoint, px=40):
    """A filled Material Symbols Rounded glyph in white (tinted by the watch face)."""
    f = ImageFont.truetype(SYMBOLS, px)
    vals = []
    for a in f.get_variation_axes():
        n = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
        vals.append({"Fill": 1, "Weight": 600, "Optical size": 24, "Grade": 0}.get(n, a["default"]))
    f.set_variation_by_axes(vals)
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((px / 2, px / 2), chr(codepoint), font=f, fill=(255, 255, 255, 255), anchor="mm")
    return im


def launcher_icon(size=192):
    ss = 4
    n = size * ss
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([0, 0, n - 1, n - 1], fill=(0, 0, 0, 255))
    t = tag("9–5", 64, 10, seed=41, scale=ss, drips=3)
    red = Image.new("RGBA", t.size, (232, 36, 44, 255))
    red.putalpha(t.getchannel("A"))
    s = min(1.0, (n * 0.78) / max(t.size))
    red = red.resize((int(t.width * s), int(t.height * s)), Image.LANCZOS)
    im.alpha_composite(red, (int((n - red.width) / 2), int((n - red.height) / 2)))
    return im.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(DRAWABLE, exist_ok=True)
    meta = {}
    for name, text in (("tag_full", "FUCK 9–5"), ("tag_boss", "F*CK 9–5")):
        img = tag(text, 64, 8, seed=7)
        img.save(os.path.join(DRAWABLE, name + ".png"), optimize=True)
        meta[name] = {"w": img.width / 2, "h": img.height / 2}
    for f in os.listdir(DRAWABLE):
        if f.startswith(("dab_", "seg_")):
            os.remove(os.path.join(DRAWABLE, f))
    segs = []
    for k, (piece, (x, y, w, h)) in enumerate(progress_segments()):
        piece.save(os.path.join(DRAWABLE, f"seg_{k}.png"), optimize=True)
        segs.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
    meta["segments"] = segs
    img, (x, y) = track()
    img.save(os.path.join(DRAWABLE, "work_track.png"), optimize=True)
    meta["work_track"] = {"x": x, "y": y, "w": img.width, "h": img.height}
    launcher_icon().save(os.path.join(DRAWABLE, "ic_launcher.png"), optimize=True)
    for name, cp in ICONS.items():
        symbol(cp).save(os.path.join(DRAWABLE, name + ".png"), optimize=True)
    with open(os.path.join(HERE, "assets.json"), "w") as f:
        json.dump(meta, f, indent=1)
    for fn in sorted(os.listdir(DRAWABLE)):
        im = Image.open(os.path.join(DRAWABLE, fn))
        print(f"{fn}: {im.size}, {os.path.getsize(os.path.join(DRAWABLE, fn))} bytes")


if __name__ == "__main__":
    main()

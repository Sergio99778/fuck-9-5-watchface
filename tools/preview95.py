"""Previews of the 9-5 face, rendered from its own watchface.xml."""
import datetime as dt
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design95 as design  # noqa: E402
from wffrender import Env, Renderer  # noqa: E402

OUT = os.path.join(design.PROJECT, "previews")
FALLBACK = "/home/claude/work/orbit/tools/_system_font.ttf"


def renderer():
    return Renderer(os.path.join(design.RES, "raw", "watchface.xml"), design.RES, scale=4, fallback_font=FALLBACK)


def render(r, when, ambient=False, spray=None, boss="FALSE", is24h=False, size=450, extra=None):
    cfg = {"boss": boss}
    if spray:
        cfg["spray"] = spray
    data = {"__complications__": {}, "STEP_COUNT": 6832, "STEP_GOAL": 10000, "STEP_PERCENT": 68,
            "BATTERY_PERCENT": 76, "BATTERY_CHARGING_STATUS": False, "BATTERY_IS_LOW": False,
            "HEART_RATE": 72, "WEATHER.IS_AVAILABLE": True, "WEATHER.UV_INDEX": 5}
    data.update(extra or {})
    env = Env(dt=when, ambient=ambient, is24h=is24h, config=cfg, extra=data)
    return r.render(env, out_size=size)


def round_mask(img, bezel=True):
    n = img.size[0]
    pad = int(n * 0.07) if bezel else 0
    out = Image.new("RGBA", (n + 2 * pad, n + 2 * pad), (0, 0, 0, 0))
    ss = 4
    m = Image.new("L", (n * ss, n * ss), 0)
    ImageDraw.Draw(m).ellipse([0, 0, n * ss - 1, n * ss - 1], fill=255)
    m = m.resize((n, n), Image.LANCZOS)
    if bezel:
        big = (n + 2 * pad) * ss
        b = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(b)
        d.ellipse([0, 0, big - 1, big - 1], fill=(38, 40, 44, 255))
        e = int(pad * ss * 0.35)
        d.ellipse([e, e, big - 1 - e, big - 1 - e], fill=(10, 10, 12, 255))
        out.alpha_composite(b.resize((n + 2 * pad, n + 2 * pad), Image.LANCZOS))
    face = img.copy()
    face.putalpha(m)
    out.alpha_composite(face, (pad, pad))
    return out


def sheet(items, cols, name):
    lab = ImageFont.truetype(os.path.join(design.RES, "font", "n95_label.ttf"), 26)
    tiles = []
    for label, img in items:
        t = round_mask(img)
        c = Image.new("RGBA", (t.width, t.height + 44), (18, 18, 20, 255))
        c.alpha_composite(t)
        ImageDraw.Draw(c).text((t.width / 2, t.height + 20), label, font=lab, fill=(210, 210, 210), anchor="mm")
        tiles.append(c)
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGBA", (cols * tw, rows * th), (18, 18, 20, 255))
    for i, t in enumerate(tiles):
        out.alpha_composite(t, ((i % cols) * tw, (i // cols) * th))
    os.makedirs(OUT, exist_ok=True)
    out.convert("RGB").save(os.path.join(OUT, name))


MON = dt.datetime(2026, 9, 28)   # a Monday
FRI = dt.datetime(2026, 10, 2)
SAT = dt.datetime(2026, 10, 3)

if __name__ == "__main__":
    design.write_all()
    r = renderer()
    what = sys.argv[1] if len(sys.argv) > 1 else "states"
    if what == "states":
        cases = [
            ("LUN 7:40", MON.replace(hour=7, minute=40)),
            ("LUN 8:35", MON.replace(hour=8, minute=35)),
            ("LUN 10:08", MON.replace(hour=10, minute=8, second=32)),
            ("LUN 16:21", MON.replace(hour=16, minute=21)),
            ("LUN 18:30", MON.replace(hour=18, minute=30)),
            ("VIE 17:05", FRI.replace(hour=17, minute=5)),
            ("SÁB 11:00", SAT.replace(hour=11)),
            ("24 H 13:45", MON.replace(hour=13, minute=45)),
            ("SIEMPRE ACTIVA", MON.replace(hour=10, minute=8)),
        ]
        items = []
        for label, when in cases:
            items.append((label, render(r, when, is24h=label.startswith("24"), ambient=label == "SIEMPRE ACTIVA")))
        sheet(items, 3, "states.png")
    elif what == "colors":
        items = [(name.upper(), render(r, MON.replace(hour=10, minute=8, second=32), spray=i)) for i, name, _ in design.SPRAYS]
        sheet(items, 3, "colors.png")
    elif what == "boss":
        sheet([("NORMAL", render(r, MON.replace(hour=10, minute=8, second=32))),
               ("MODO JEFE", render(r, MON.replace(hour=10, minute=8, second=32), boss="TRUE"))], 2, "boss.png")
    elif what == "hero":
        img = render(r, MON.replace(hour=10, minute=8, second=32), size=900)
        round_mask(img).save(os.path.join(OUT, "hero.png"))

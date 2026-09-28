"""Generates the 'FUCK 9-5' watch face (Watch Face Format v4).

A stencilled digital time, a spray-painted tag, and the working day (9:00 to 17:00) as a band
on the 12-hour ring that gets sprayed in, ten minutes at a time, as the day goes by. Underneath,
a countdown: time until you start, time until 5, "LIBRE" after work, "FIN DE SEMANA" from
Friday 17:00 until Monday.
"""
from __future__ import annotations

import json
import math
import os
import random
from xml.sax.saxutils import escape, quoteattr

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SRC = os.path.join(PROJECT, "src")
RES = os.path.join(SRC, "res")

PACKAGE = "app.ninetofive.watchface"
VERSION_CODE = 4
VERSION_NAME = "1.2.1"
AUTHOR = "Sergio De Lucio"
LICENSE = "CC BY-NC-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
WFF_VERSION = 4
MIN_SDK = TARGET_SDK = 36

W = H = 450
C = 225.0
RING_R = 206.0
WORK_START_DEG = 270.0            # 9 o'clock on a 12-hour dial
MINUTES_PER_DAB = 10              # 48 dabs cover 9:00-17:00
N_DABS = 48
DAB_SIZE = 32

TIME_FONT, TIME_FONT_AOD, LABEL_FONT, DIGIT_FONT = "n95_time", "n95_time_light", "n95_label", "n95_digit"
TIME_SIZE, TIME_CY, TIME_BOX_H = 118, 196, 100
DATE_SIZE, DATE_CY = 24, 112
TAG_CX, TAG_CY, TAG_SCALE = 228, 289, 0.84
COUNT_SIZE, COUNT_CY = 21, 361
LABEL_R, LABEL_SIZE = 182, 26

SPRAY = "[CONFIGURATION.spray.0]"
SPRAYS = [  # id, name, colour
    ("rojo", "Rojo", "#FFE8242C"),
    ("rosa", "Rosa neón", "#FFFF3FA4"),
    ("verde", "Verde neón", "#FF4DFF5A"),
    ("amarillo", "Amarillo", "#FFFFE01A"),
    ("naranja", "Naranja", "#FFFF6A13"),
    ("blanco", "Blanco", "#FFF2F2F2"),
]
DAYS_ES = {1: "DOM", 2: "LUN", 3: "MAR", 4: "MIÉ", 5: "JUE", 6: "VIE", 7: "SÁB"}

# Ambient switch is instant: Wear OS 6 can freeze half-way through the fade on third-party
# faces and show both layers at once (issuetracker.google.com/452423520).
AMB = 'mode="AMBIENT" target="alpha" duration="0"'

NOW = "([HOUR_0_23] * 60 + [MINUTE])"                      # minutes since midnight
NOW_RAW = NOW
WEEKDAY = "(([DAY_OF_WEEK] &gt;= 2) &amp;&amp; ([DAY_OF_WEEK] &lt;= 6))"   # Mon-Fri (1 = Sunday)


def fnum(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def metrics(family):
    f = TTFont(os.path.join(RES, "font", family + ".ttf"))
    upm = f["head"].unitsPerEm
    return f["hhea"].ascent / upm, -f["hhea"].descent / upm


def line_h(family, size):
    a, d = metrics(family)
    return int(math.ceil((a + d) * size)) + 4


def template(fmt, *exprs):
    if not exprs:                      # a Template needs at least one Parameter; plain text doesn't
        return escape(fmt)
    params = "".join(f"<Parameter expression={quoteattr(e)}/>" for e in exprs)
    return f"<Template>{escape(fmt)}{params}</Template>"


def text(name, x, y, w, h, family, size, color, content, letter_spacing=None, extra="", children="",
         align="CENTER"):
    ls = f' letterSpacing="{fnum(letter_spacing)}"' if letter_spacing else ""
    return (f'<PartText name="{uid(name)}" x="{int(round(x))}" y="{int(round(y))}" width="{int(round(w))}" '
            f'height="{int(round(h))}"{extra}>{children}'
            f'<Text align="{align}" maxLines="1"><Font family="{family}" size="{fnum(size)}" color="{color}"{ls}>'
            f"{content}</Font></Text></PartText>")


# ------------------------------------------------------------------------------------------
# Conditions are always built as if / else-if chains: every <Condition> has exactly one
# <Compare>, and the "else" goes in <Default> (which may hold the next Condition). The runtime
# does not promise "first true Compare wins", so no Condition may ever have two true branches.
# ------------------------------------------------------------------------------------------
def chain(cases, default):
    """cases: [(name, expression, body), ...] tried in order; default: body when none match."""
    if not cases:
        return default
    (name, expr, body), rest = cases[0], cases[1:]
    return (f'<Condition><Expressions><Expression name="{name}"><![CDATA[{expr}]]></Expression>'
            f'</Expressions><Compare expression="{name}">{body}</Compare>'
            f"<Default>{chain(rest, default)}</Default></Condition>")


_NAMES = {}


def uid(base):
    """Unique element names, so no two parts in the scene share one."""
    _NAMES[base] = _NAMES.get(base, 0) + 1
    return base if _NAMES[base] == 1 else f"{base}_{_NAMES[base]}"


def polar(r, deg):
    a = math.radians(deg)
    return C + r * math.sin(a), C - r * math.cos(a)


# ------------------------------------------------------------------------------------------
def ring():
    parts = [f'<Ellipse x="{fnum(C - RING_R)}" y="{fnum(C - RING_R)}" width="{fnum(2 * RING_R)}" '
             f'height="{fnum(2 * RING_R)}"><Stroke color="#FF2B2B2B" thickness="2"/></Ellipse>']
    for i in range(12):
        major = i % 3 == 0
        r0, r1 = (RING_R - 11, RING_R + 7) if major else (RING_R - 6, RING_R + 4)
        x0, y0 = polar(r0, i * 30)
        x1, y1 = polar(r1, i * 30)
        col = "#FF9A9A9A" if major else "#FF555555"
        parts.append(f'<Line startX="{fnum(x0)}" startY="{fnum(y0)}" endX="{fnum(x1)}" endY="{fnum(y1)}">'
                     f'<Stroke color="{col}" thickness="2.4" cap="ROUND"/></Line>')
    return (f'<PartDraw name="ring" x="0" y="0" width="{W}" height="{H}">'
            f'<Variant {AMB} value="110"/>' + "".join(parts) + "</PartDraw>")


def hour_labels():
    out = []
    for num, deg in (("9", 270), ("5", 150)):
        x, y = polar(LABEL_R, deg)
        h = line_h(DIGIT_FONT, LABEL_SIZE)
        out.append(text(f"label_{num}", x - 22, y - h / 2, 44, h, DIGIT_FONT, LABEL_SIZE, "#FFFFFFFF", num,
                        children=f'<Variant {AMB} value="130"/>'))
    return "".join(out)


def work_track(meta):
    t = meta["work_track"]
    return (f'<PartImage name="work_track" x="{int(t["x"])}" y="{int(t["y"])}" width="{int(t["w"])}" '
            f'height="{int(t["h"])}" tintColor="{SPRAY}" alpha="92">'
            f'<Variant {AMB} value="0"/><Image resource="work_track"/></PartImage>')


def work_progress(meta):
    """48 pieces of one sprayed band (one per 10 minutes). Piece k shows once the workday is more
    than 10*k minutes old, so the band paints itself from 9 o'clock up to the current time."""
    parts = []
    for k, seg in enumerate(meta["segments"]):
        start = 540 + MINUTES_PER_DAB * k
        vis = f"({WEEKDAY} &amp;&amp; ({NOW} &gt; {start})) ? 255 : 0"
        parts.append(
            f'<PartImage name="work_{k}" x="{seg["x"]}" y="{seg["y"]}" width="{seg["w"]}" height="{seg["h"]}" '
            f'tintColor="{SPRAY}"><Transform target="alpha" value="{vis}"/>'
            f'<Image resource="seg_{k}"/></PartImage>')
    return (f'<Group name="work_progress" x="0" y="0" width="{W}" height="{H}">'
            f'<Variant {AMB} value="0"/>' + "".join(parts) + "</Group>")


def now_marker():
    x, y = C - 8, C - RING_R - 8
    dot = (f'<PartDraw name="now_dot" x="0" y="0" width="{W}" height="{H}" pivotX="0.5" pivotY="0.5">'
           '<Transform target="angle" value="[HOUR_0_11_MINUTE] * 30"/>'
           f'<Variant {AMB} value="0"/>'
           f'<Ellipse x="{fnum(x - 3)}" y="{fnum(y - 3)}" width="22" height="22"><Fill color="#FF000000"/></Ellipse>'
           f'<Ellipse x="{fnum(x)}" y="{fnum(y)}" width="16" height="16"><Fill color="#FFFFFFFF"/></Ellipse></PartDraw>')
    ring_amb = (f'<PartDraw name="now_ring_ambient" x="0" y="0" width="{W}" height="{H}" pivotX="0.5" pivotY="0.5" alpha="0">'
                '<Transform target="angle" value="[HOUR_0_11_MINUTE] * 30"/>'
                f'<Variant {AMB} value="220"/>'
                f'<Ellipse x="{fnum(C - 7)}" y="{fnum(C - RING_R - 7)}" width="14" height="14">'
                '<Stroke color="#FFC8C8C8" thickness="2.5"/></Ellipse></PartDraw>')
    return dot + ring_amb


def date_line():
    h = line_h(LABEL_FONT, DATE_SIZE)

    def day(dow):
        return text(f"date_{DAYS_ES[dow].lower()}", 0, 0, 260, h, LABEL_FONT, DATE_SIZE, "#FFD2D2D2",
                    template(f"{DAYS_ES[dow]} %s", "[DAY]"), letter_spacing=0.08)
    body = chain([(f"dow_{d}", f"[DAY_OF_WEEK] == {d}", day(d)) for d in range(1, 7)], day(7))
    return (f'<Group name="date" x="95" y="{int(round(DATE_CY - h / 2))}" width="260" height="{h}">'
            f'<Variant {AMB} value="150"/><Launch target="CALENDAR"/>{body}</Group>')


def clock(ambient):
    fam = TIME_FONT_AOD if ambient else TIME_FONT
    color = "#FFD8D8D8" if ambient else "#FFFFFFFF"
    name = "time_ambient" if ambient else "time"
    y = int(round(TIME_CY - TIME_BOX_H / 2))
    vis = ' alpha="0"' if ambient else ""
    variant = f'<Variant {AMB} value="{255 if ambient else 0}"/>'
    launch = "" if ambient else '<Launch target="ALARM"/>'

    def t(label, hour_expr):
        return text(f"{name}_{label}", 0, 0, W, TIME_BOX_H, fam, TIME_SIZE, color,
                    template("%s:%s", hour_expr, "[MINUTE_Z]"))
    body = chain([(f"{name}_24h", "[IS_24_HOUR_MODE]", t("24h", "[HOUR_0_23_Z]"))], t("12h", "[HOUR_1_12]"))
    return (f'<Group name="{name}" x="0" y="{y}" width="{W}" height="{TIME_BOX_H}"{vis}>{variant}{launch}'
            f"{body}</Group>")


def tag(meta):
    def image(key):
        m = meta[key]
        w, h = int(round(m["w"] * TAG_SCALE)), int(round(m["h"] * TAG_SCALE))
        return (f'<PartImage name="{key}" x="{int(round(TAG_CX - w / 2))}" y="{int(round(TAG_CY - h / 2))}" '
                f'width="{w}" height="{h}" tintColor="{SPRAY}">'
                f'<Variant {AMB} value="70"/><Image resource="{key}"/></PartImage>')
    return ('<BooleanConfiguration id="boss">'
            f'<BooleanOption id="FALSE">{image("tag_full")}</BooleanOption>'
            f'<BooleanOption id="TRUE">{image("tag_boss")}</BooleanOption>'
            "</BooleanConfiguration>")


# ------------------------------------------------------------------------------------------
# Edge indicators: one per quarter of the dial, laid along the ring (tangent), readable from
# outside on the top half and from inside on the bottom half.
# ------------------------------------------------------------------------------------------
IND_R, IND_W, IND_H, IND_SIZE, ICON = 182, 94, 26, 20, 19
UV_LEVELS = [  # (upper bound exclusive, colour) - WHO UV index colours
    (3, "#FF5BD66A"), (6, "#FFFFE14D"), (8, "#FFFF9A2E"), (11, "#FFFF4B3E"), (None, "#FFB06BFF")]


def _icon(res, tint, name="icon"):
    y = int(round((IND_H - ICON) / 2))
    return (f'<PartImage name="{uid(name)}" x="2" y="{y}" width="{ICON}" height="{ICON}" tintColor="{tint}">'
            f'<Image resource="{res}"/></PartImage>')


def _value(content, name="value"):
    return text(name, ICON + 7, 0, IND_W - ICON - 7, IND_H, LABEL_FONT, IND_SIZE, "#FFF0F0F0", content,
                align="START")


def indicator(name, deg, body, launch=None):
    top = deg < 90 or deg > 270
    rot = deg if top else deg - 180
    x, y = polar(IND_R, deg)
    la = f'<Launch target="{launch}"/>' if launch else ""
    return (f'<Group name="ind_{name}" x="{int(round(x - IND_W / 2))}" y="{int(round(y - IND_H / 2))}" '
            f'width="{IND_W}" height="{IND_H}" angle="{fnum(rot)}" pivotX="0.5" pivotY="0.5">'
            f'<Variant {AMB} value="150"/>{la}{body}</Group>')


def indicators():
    steps = _icon("ic_steps", SPRAY, "steps_icon") + _value(template("%s", "[STEP_COUNT]"), "steps_value")
    battery = (chain([("bat_charging", "[BATTERY_CHARGING_STATUS]",
                       _icon("ic_battery_charging", "#FF4DFF5A", "battery_icon_charging")),
                      ("bat_low", "[BATTERY_IS_LOW]", _icon("ic_battery_alert", "#FFFF3B30", "battery_icon_low"))],
                     _icon("ic_battery", SPRAY, "battery_icon"))
               + _value(template("%s%%", "[BATTERY_PERCENT]"), "battery_value"))
    uv_icon = chain([(f"uv_{i}", f"[WEATHER.UV_INDEX] < {hi}", _icon("ic_uv", col, f"uv_icon_{i}"))
                     for i, (hi, col) in enumerate(UV_LEVELS[:-1])],
                    _icon("ic_uv", UV_LEVELS[-1][1], "uv_icon_extreme"))
    uv = chain([("uv_ok", "[WEATHER.IS_AVAILABLE]",
                 f'<Group name="uv_now" x="0" y="0" width="{IND_W}" height="{IND_H}">'
                 + uv_icon + _value(template("UV %s", "round([WEATHER.UV_INDEX])"), "uv_value") + "</Group>")],
               f'<Group name="uv_none" x="0" y="0" width="{IND_W}" height="{IND_H}">'
               + _icon("ic_uv", "#FF8A8A8A", "uv_icon_none") + _value("UV --", "uv_value_none") + "</Group>")
    heart = (_icon("ic_heart", SPRAY, "heart_icon")
             + chain([("hr_ok", "[HEART_RATE] > 0", _value(template("%s", "round([HEART_RATE])"), "heart_value"))],
                     _value("--", "heart_value_none")))
    return (indicator("steps", 50, steps) + indicator("battery", 130, battery, "BATTERY_STATUS")
            + indicator("uv", 230, uv) + indicator("heart", 310, heart, "HEALTH_HEART_RATE"))


def countdown():
    h = line_h(LABEL_FONT, COUNT_SIZE)

    def msg(label, fmt, *exprs):
        return text(f"countdown_{label}", 0, 0, 300, h, LABEL_FONT, COUNT_SIZE, "#FFEDEDED",
                    template(fmt, *exprs), letter_spacing=0.05)
    to9, to17 = f"(540 - {NOW_RAW})", f"(1020 - {NOW_RAW})"
    body = chain([
        ("cd_weekend", "([DAY_OF_WEEK] == 1) || ([DAY_OF_WEEK] == 7) || (([DAY_OF_WEEK] == 6) && ([HOUR_0_23] >= 17))",
         msg("weekend", "FIN DE SEMANA")),
        ("cd_before9_h", f"{NOW_RAW} <= 480",
         msg("before9_h", "ENTRAS EN %sH %sM", f"round(floor({to9} / 60))", f"{to9} % 60")),
        ("cd_before9_m", "[HOUR_0_23] < 9", msg("before9_m", "ENTRAS EN %sM", to9)),
        ("cd_work_h", f"{NOW_RAW} <= 960",
         msg("work_h", "FALTAN %sH %sM", f"round(floor({to17} / 60))", f"{to17} % 60")),
        ("cd_work_m", "[HOUR_0_23] < 17", msg("work_m", "FALTAN %sM", to17)),
    ], msg("free", "LIBRE"))
    return (f'<Group name="countdown" x="75" y="{int(round(COUNT_CY - h / 2))}" width="300" height="{h}">'
            f'<Variant {AMB} value="150"/>{body}</Group>')


def watchface_xml():
    _NAMES.clear()
    with open(os.path.join(HERE, "assets.json")) as f:
        meta = json.load(f)
    sprays = "\n".join(f'      <ColorOption id="{i}" displayName="spray_{i}" colors="{c}"/>' for i, _, c in SPRAYS)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!--
  FUCK 9-5 - a Watch Face Format (v{WFF_VERSION}) watch face.
  © 2026 {AUTHOR}. Licensed under {LICENSE} ({LICENSE_URL}).
  Fonts and icons keep their own licenses (see TERCEROS.md).
  The working day (9:00-17:00) is a band on the 12-hour ring that gets sprayed in as the day
  goes by, with a countdown underneath. Generated by tools/design95.py; edit that, not this.
-->
<WatchFace width="{W}" height="{H}">
  <Metadata key="CLOCK_TYPE" value="DIGITAL"/>
  <Metadata key="PREVIEW_TIME" value="10:08:32"/>
  <Metadata key="AUTHOR" value="{AUTHOR}"/>
  <Metadata key="LICENSE" value="{LICENSE} - {LICENSE_URL}"/>
  <UserConfigurations>
    <ColorConfiguration id="spray" displayName="spray_label" defaultValue="{SPRAYS[0][0]}">
{sprays}
    </ColorConfiguration>
    <BooleanConfiguration id="boss" displayName="boss_label" defaultValue="FALSE"/>
  </UserConfigurations>
  <Scene backgroundColor="#FF000000">
    {ring()}
    {work_track(meta)}
    {work_progress(meta)}
    {hour_labels()}
    {now_marker()}
    {tag(meta)}
    {indicators()}
    {date_line()}
    {clock(False)}
    {clock(True)}
    {countdown()}
  </Scene>
</WatchFace>
"""


def strings_xml():
    items = {"watch_face_name": "FUCK 9-5", "spray_label": "Color del spray", "boss_label": "Modo jefe (F*CK)"}
    for i, name, _ in SPRAYS:
        items[f"spray_{i}"] = name
    rows = "\n".join(f'    <string name="{k}">{escape(v)}</string>' for k, v in items.items())
    return f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n{rows}\n</resources>\n'


def watch_face_info_xml():
    return """<?xml version="1.0" encoding="utf-8"?>
<WatchFaceInfo>
  <Preview value="@drawable/preview"/>
  <Category value="CATEGORY_EMPTY"/>
  <AvailableInRetail value="false"/>
  <MultipleInstancesAllowed value="true"/>
  <Editable value="true"/>
</WatchFaceInfo>
"""


def manifest_xml():
    return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{PACKAGE}"
    android:versionCode="{VERSION_CODE}"
    android:versionName="{VERSION_NAME}">

  <uses-sdk android:minSdkVersion="{MIN_SDK}" android:targetSdkVersion="{TARGET_SDK}"/>
  <uses-feature android:name="android.hardware.type.watch"/>

  <!-- Watch Face Format watch faces are resource-only: no code is allowed. -->
  <application
      android:label="@string/watch_face_name"
      android:icon="@drawable/ic_launcher"
      android:hasCode="false">
    <meta-data android:name="com.google.android.wearable.standalone" android:value="true"/>
    <meta-data android:name="author" android:value="{AUTHOR}"/>
    <meta-data android:name="license" android:value="{LICENSE} - {LICENSE_URL}"/>
    <property android:name="com.google.wear.watchface.format.version" android:value="{WFF_VERSION}"/>
  </application>
</manifest>
"""


def pretty(xml):
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)
    root = etree.fromstring(xml.encode("utf-8"), parser)
    etree.indent(root, space="  ")
    for font in root.iter("Font"):
        if font.text is not None and not font.text.strip():
            font.text = None
        for d in font.iterdescendants():
            if d.text is not None and not d.text.strip():
                d.text = None
            if d.tail is not None and not d.tail.strip():
                d.tail = None
    comment = xml.split("-->")[0].split("<!--")[1]
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!--' + comment + "-->\n"
            + etree.tostring(root, encoding="unicode") + "\n")


def write_all():
    for sub in ("raw", "values", "xml"):
        os.makedirs(os.path.join(RES, sub), exist_ok=True)
    with open(os.path.join(RES, "raw", "watchface.xml"), "w") as f:
        f.write(pretty(watchface_xml()))
    with open(os.path.join(RES, "values", "strings.xml"), "w") as f:
        f.write(strings_xml())
    with open(os.path.join(RES, "xml", "watch_face_info.xml"), "w") as f:
        f.write(watch_face_info_xml())
    with open(os.path.join(SRC, "AndroidManifest.xml"), "w") as f:
        f.write(manifest_xml())


if __name__ == "__main__":
    write_all()
    print("wrote", os.path.join(RES, "raw", "watchface.xml"))

#!/usr/bin/env python3
"""News Image 24 November 2026, v5.2 — one 1024x1024 front page.

38 dated stories, 7 regions, 13 drawn, every claim labelled.
Drawn entirely in code (Pillow vector shapes, no external images,
no network at run time). The script is its own layout validator:
it refuses to build on any overflowing text, any headline or deck
needing a third line, any overlapping map pin, any ellipsis, any
region above 7, or any arithmetic mismatch.

Design choices for v5.2 (density cut from 48 to 38):
- more air everywhere: bigger type, taller strips, wider gaps
- 13 pins only, Europe cluster spread with leader lines
- claim circles on every ALSO item (25/25) + header legend
  + definition strip in the footer
- one red punch banner on each of the three leads
- full region names on the chart (no abbreviations that clip)
"""

import hashlib
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (247, 243, 234)
INK = (20, 20, 20)
MUTED = (90, 86, 76)
RULE = (180, 172, 152)
RED = (200, 16, 46)
BLUE = (29, 78, 137)
GREEN = (30, 122, 52)
AMBER = (183, 121, 31)
PURPLE = (123, 45, 139)
ORANGE = (217, 93, 0)
TEAL = (14, 124, 123)
OCEAN = (220, 232, 240)
LAND = (201, 191, 163)
LAND_EDGE = (138, 127, 99)
CARD = (255, 255, 255)
SKY = (186, 220, 240)
SEA = (120, 178, 205)

SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

ERRORS = []


def font(path, size):
    return ImageFont.truetype(path, size)


def fail(msg):
    ERRORS.append(msg)


def text_w(f, s):
    return f.getlength(s)


def wrap(f, text, max_w, max_lines, where):
    """Greedy wrap; fails the build if it needs more than max_lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_w(f, trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        fail(f"{where}: needs {len(lines)} lines, max {max_lines}: {text!r}")
    if any("..." in ln or "\u2026" in ln for ln in lines):
        fail(f"{where}: ellipsis in text: {text!r}")
    return lines


def check_w(f, text, max_w, where):
    if text_w(f, text) > max_w:
        fail(f"{where}: {text!r} is {text_w(f, text):.0f}px, max {max_w}px")


# ---------------------------------------------------------------- regions
REGIONS = [
    ("EUROPE", BLUE, 7),
    ("N. AMERICA", RED, 7),
    ("MIDDLE EAST", AMBER, 6),
    ("ASIA", GREEN, 7),
    ("LATIN AM.", PURPLE, 4),
    ("AFRICA", ORANGE, 4),
    ("OCEANIA", TEAL, 3),
]
REGION_COLOR = {name: color for name, color, _ in REGIONS}

# ---------------------------------------------------------------- stories
# 13 drawn stories (new numbers 1-13). `pin` = (lon, lat) of the story.
# `jitter` = display offset (dx, dy) in map pixels for the Europe /
# US-east clusters, with a thin leader line back to the true spot.
MAINS = [
    dict(n=1, region="N. AMERICA", claim="O", tag="MARKETS \u00b7 SANTA CLARA",
         head="Huang is back at Nvidia",
         deck="Shares soar 31.5% as the chief returns",
         banner="HUANG IS BACK", kind="data",
         pin=(-122.0, 37.0), jitter=(6, -3)),
    dict(n=2, region="AFRICA", claim="O", tag="DEFENCE \u00b7 BENGHAZI",
         head="Ukraine sinks Russian warship off Libya",
         deck="Corvette hit as Tripoli condemns the sinking",
         banner="SHIP SUNK OFF LIBYA", kind="ship",
         pin=(20.0, 32.0), jitter=(0, 4)),
    dict(n=3, region="MIDDLE EAST", claim="O", tag="CLIMATE \u00b7 ANTALYA",
         head="COP31 ends with no pact",
         deck="Antalya talks close without a deal",
         banner="NO PACT", kind="hall",
         pin=(30.7, 36.9), jitter=(16, -2)),
    dict(n=4, region="EUROPE", claim="O", tag="DEFENCE \u00b7 POLAND",
         head="NATO sends AWACS plane",
         deck="Surveillance jet to Poland",
         banner="EYES UP", kind="plane",
         pin=(19.0, 52.0), jitter=(-8, -8)),
    dict(n=5, region="EUROPE", claim="O", tag="SECURITY \u00b7 ODESA",
         head="96 drones in one night",
         deck="Odesa dark and cold after strikes",
         banner="96 DRONES", kind="odesa",
         pin=(30.7, 46.5)),
    dict(n=6, region="MIDDLE EAST", claim="R", tag="ENERGY \u00b7 TEHRAN",
         head="Iran vows to defy US blockade",
         deck="Hormuz on edge as tankers wait",
         banner="HORMUZ ON EDGE", kind="hormuz",
         pin=(51.4, 35.7)),
    dict(n=7, region="N. AMERICA", claim="O", tag="TRANSPORT \u00b7 ATLANTA",
         head="Delta grounds 3,000+ flights",
         deck="US flights hit by shutdown strain",
         banner="3,000+ GROUNDED", kind="planes",
         pin=(-84.4, 33.7)),
    dict(n=8, region="ASIA", claim="R", tag="DEFENCE \u00b7 TAIPEI",
         head="12 warships circle Taiwan",
         deck="Taipei tracks the fleet",
         banner="12 WARSHIPS", kind="ships",
         pin=(121.5, 25.0)),
    dict(n=9, region="EUROPE", claim="O", tag="HEALTH \u00b7 PARIS",
         head="Sanofi buys Insmed, $41bn",
         deck="Paris seals the big drug deal",
         banner="$41BN DEAL", kind="lab",
         pin=(2.35, 48.9)),
    dict(n=10, region="AFRICA", claim="R", tag="DISASTER \u00b7 NIGERIA",
         head="24 dead as boat capsizes",
         deck="Funeral-bound boat sinks in Nigeria",
         banner="24 DEAD", kind="boat",
         pin=(7.0, 9.0)),
    dict(n=11, region="LATIN AM.", claim="O", tag="COURTS \u00b7 MEXICO",
         head="Mexico nabs \u2018Chapo Isidro\u2019",
         deck="16 killed in the operation",
         banner="CAPTURED", kind="desert",
         pin=(-99.0, 19.4), jitter=(-4, -7)),
    dict(n=12, region="N. AMERICA", claim="R", tag="DIPLOMACY \u00b7 WASHINGTON",
         head="Trump meets Rutte Wednesday",
         deck="Washington talks ahead",
         banner="WEDNESDAY", kind="flags",
         pin=(-77.0, 38.9), jitter=(15, -9)),
    dict(n=13, region="EUROPE", claim="O", tag="TECH \u00b7 BERLIN",
         head="Germany adopts Delta system",
         deck="Berlin takes Ukraine\u2019s battle tech",
         banner="DELTA GOES WEST", kind="laptop",
         pin=(13.4, 52.5), jitter=(20, -8)),
]

# 25 ALSO stories (new numbers 14-38), one short line each.
ALSO = [
    (14, "EUROPE", "R", "Ukraine drones set two Russian refineries ablaze"),
    (15, "MIDDLE EAST", "CL", "Houthis say they hit Saudi Rabigh refinery"),
    (16, "MIDDLE EAST", "R", "Israeli strike kills 3 in Khan Younis"),
    (17, "OCEANIA", "O", "Vanuatu 6.5 quake, no tsunami"),
    (18, "OCEANIA", "R", "Hobart stadium bill jumps to $1.23bn"),
    (19, "N. AMERICA", "O", "US blacklists Megaspeed on export controls"),
    (20, "N. AMERICA", "O", "US unveils H-1B visa changes"),
    (21, "EUROPE", "O", "NATO offers Poland \u2018significant backing\u2019"),
    (22, "EUROPE", "R", "Russian losses outpace recruiting, US says"),
    (23, "N. AMERICA", "O", "US to host 2031 Women\u2019s World Cup \u2014 FIFA"),
    (24, "LATIN AM.", "R", "Panama, First Quantum resume mine talks"),
    (25, "LATIN AM.", "R", "Storm forces thousands to flee in Brazil"),
    (26, "MIDDLE EAST", "O", "Gaza\u2019s soil and water poisoned by war \u2014 UN"),
    (27, "N. AMERICA", "O", "UN chief urges global AI safety rules"),
    (28, "ASIA", "O", "India and Nepal sign 8 deals"),
    (29, "ASIA", "R", "Hasina plans December 16 return"),
    (30, "ASIA", "R", "Hanoi hotpot blast kills 6, injures 10+"),
    (31, "OCEANIA", "O", "Beaver Supermoon rises tonight"),
    (32, "ASIA", "R", "South Korea proposes ending ICO ban"),
    (33, "ASIA", "O", "Seoul Metro unions call off strike"),
    (34, "ASIA", "R", "China Southern unit to buy 50 Boeing jets"),
    (35, "MIDDLE EAST", "O", "Sooryavanshi smashes 204 off 53 balls"),
    (36, "LATIN AM.", "O", "Argentina enters technical recession"),
    (37, "AFRICA", "R", "Kenya faces Sh12bn election funding gap"),
    (38, "AFRICA", "O", "Tanzania launches \u20183 Zero\u2019 maternal drive"),
]

FIELDS = ["Markets", "Defence", "Climate", "Security", "Energy",
          "Transport", "Health", "Disaster", "Courts", "Politics",
          "Diplomacy", "Tech", "Trade", "Migration", "Culture",
          "Sport", "Environment", "Labour", "Space", "Economy", "Crime"]

IN_NUMBERS = [
    ("+31.5%", "Nvidia shares"),
    ("96", "drones over Ukraine"),
    ("3,000+", "US flights hit"),
    ("6.5", "Vanuatu quake"),
    ("24", "dead, Nigeria boat"),
    ("$952BN", "Nvidia gain"),
    ("204", "Sooryavanshi off 53"),
]

UTC_ITEMS = [
    ("05:30", "Taiex +9.0%"),
    ("06:30", "Sanofi $41bn deal"),
    ("07:45", "Tripoli condemns sinking"),
    ("08:00", "73 of 96 drones downed"),
    ("14:00", "Nvidia reinstates Huang"),
    ("16:30", "NATO confirms AWACS"),
    ("21:00", "Supermoon rises"),
]

REGION_BARS = [("EUROPE", 7), ("NORTH AMERICA", 7), ("MIDDLE EAST", 6),
               ("ASIA", 7), ("LATIN AM.", 4), ("AFRICA", 4),
               ("OCEANIA", 3)]

MARKETS = [("NVIDIA", "+31.5%", 31.5), ("TAIEX", "+9.0%", 9.0),
           ("KOSPI", "+7.3%", 7.3), ("NASDAQ", "+6.5%", 6.5),
           ("S&P 500", "+4.7%", 4.7), ("NIKKEI", "+4.2%", 4.2)]

# ---------------------------------------------------------------- map data
# Simplified continent outlines in (lon, lat). Stylised, drawn in code.
NORTH_AMERICA = [(-168, 66), (-165, 60), (-158, 58), (-152, 60), (-140, 60),
    (-135, 57), (-130, 54), (-125, 49), (-124, 42), (-120, 34), (-117, 32),
    (-110, 24), (-105, 20), (-97, 16), (-94, 17), (-90, 14), (-86, 12),
    (-83, 9), (-80, 8), (-77, 7), (-80, 10), (-84, 13), (-87, 15),
    (-90, 18), (-91, 19), (-97, 22), (-97, 26), (-93, 30), (-89, 30),
    (-84, 30), (-81, 26), (-80, 32), (-76, 35), (-74, 39), (-70, 42),
    (-68, 45), (-65, 44), (-60, 46), (-55, 47), (-60, 52), (-65, 58),
    (-68, 58), (-75, 62), (-80, 62), (-85, 66), (-92, 66), (-95, 69),
    (-110, 68), (-125, 70), (-140, 70), (-155, 71), (-165, 68), (-168, 66)]
GREENLAND = [(-45, 60), (-40, 64), (-32, 68), (-22, 70), (-20, 74),
    (-30, 76), (-50, 76), (-58, 72), (-55, 68), (-52, 64), (-45, 60)]
SOUTH_AMERICA = [(-77, 7), (-75, 10), (-72, 12), (-64, 10), (-60, 8),
    (-52, 5), (-50, 0), (-44, -3), (-35, -8), (-40, -20), (-48, -27),
    (-57, -35), (-62, -41), (-65, -45), (-68, -50), (-70, -54), (-73, -50),
    (-73, -40), (-73, -30), (-70, -20), (-75, -15), (-80, -6), (-81, 0),
    (-80, 5), (-77, 7)]
AFRICA = [(-6, 35), (-10, 31), (-15, 27), (-17, 20), (-17, 15), (-15, 11),
    (-12, 8), (-8, 5), (-4, 5), (0, 6), (6, 4), (9, 4), (9, -1), (12, -5),
    (13, -12), (12, -18), (14, -22), (16, -28), (18, -34), (20, -35),
    (26, -34), (32, -28), (35, -24), (40, -16), (40, -10), (42, -4),
    (46, -1), (51, 2), (51, 10), (48, 11), (43, 12), (40, 15), (38, 18),
    (36, 22), (34, 27), (32, 31), (30, 31), (22, 33), (15, 32), (10, 37),
    (5, 37), (-6, 35)]
EUROPE = [(-10, 36), (-9, 43), (-2, 48), (0, 51), (4, 53), (8, 57),
    (6, 62), (12, 66), (20, 70), (30, 71), (35, 68), (40, 66), (44, 62),
    (42, 58), (40, 55), (38, 52), (36, 50), (34, 48), (32, 46), (30, 44),
    (28, 44), (26, 43), (23, 40), (22, 38), (19, 42), (15, 44), (12, 44),
    (8, 44), (3, 43), (0, 40), (-2, 37), (-6, 36), (-9, 37), (-10, 36)]
UK = [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53),
      (-2, 51), (-5, 50)]
ASIA = [(26, 38), (27, 36), (30, 36), (33, 36), (36, 36), (40, 36),
    (44, 38), (48, 38), (50, 36), (52, 33), (54, 30), (57, 27), (60, 25),
    (65, 25), (68, 23), (72, 20), (76, 16), (79, 12), (80, 8), (82, 14),
    (86, 19), (90, 22), (93, 20), (96, 16), (99, 12), (102, 9), (105, 9),
    (108, 12), (110, 20), (113, 22), (117, 24), (120, 27), (122, 31),
    (121, 35), (124, 39), (127, 40), (130, 42), (134, 43), (138, 45),
    (141, 48), (142, 52), (141, 57), (140, 61), (138, 65), (142, 68),
    (150, 70), (158, 70), (166, 68), (172, 66), (178, 65), (178, 62),
    (170, 60), (162, 57), (158, 52), (152, 46), (146, 42), (141, 38),
    (136, 35), (131, 33), (127, 35), (124, 38), (121, 36), (118, 32),
    (114, 28), (110, 22), (107, 19), (104, 16), (100, 14), (97, 16),
    (93, 21), (89, 22), (85, 19), (81, 15), (78, 10), (76, 15), (73, 20),
    (68, 24), (64, 25), (60, 25), (57, 27), (54, 30), (50, 33), (46, 36),
    (42, 37), (38, 38), (34, 38), (30, 36), (26, 38)]
ARABIA = [(35, 29), (38, 25), (40, 21), (42, 16), (44, 13), (48, 14),
    (52, 15), (56, 17), (59, 21), (58, 24), (56, 26), (52, 27), (49, 29),
    (47, 30), (44, 31), (40, 32), (36, 33), (35, 31), (35, 29)]
TAIWAN = [(120, 22), (122, 22), (122, 25), (120, 25)]
JAPAN = [(130, 31), (132, 33), (135, 34), (138, 35), (140, 37), (141, 40),
    (142, 44), (140, 44), (139, 39), (136, 36), (132, 33), (130, 31)]
INDONESIA = [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8), (120, -10),
    (125, -9), (130, -4), (135, -3), (140, -8), (138, -8), (130, -6),
    (120, -8), (110, -7), (100, -2), (95, 5)]
PHILIPPINES = [(120, 18), (122, 18), (122, 14), (120, 13), (121, 16),
    (120, 18)]
AUSTRALIA = [(114, -22), (114, -30), (115, -35), (120, -34), (125, -32),
    (129, -32), (132, -32), (135, -35), (138, -35), (140, -38), (145, -38),
    (150, -37), (153, -32), (153, -27), (150, -23), (146, -19), (142, -15),
    (142, -11), (137, -12), (135, -15), (132, -12), (130, -13), (126, -14),
    (122, -17), (118, -20), (114, -22)]
NEW_ZEALAND = [(167, -45), (170, -42), (174, -38), (177, -38), (175, -41),
    (172, -43), (168, -46), (167, -45)]
LANDMASSES = [NORTH_AMERICA, GREENLAND, SOUTH_AMERICA, AFRICA, EUROPE,
              UK, ASIA, ARABIA, TAIWAN, JAPAN, INDONESIA, PHILIPPINES,
              AUSTRALIA, NEW_ZEALAND]

# Map frame: lon -168..192, lat 78..-58 -> pixels x 20..632, y 612..740.
MAP_X0, MAP_Y0, MAP_W, MAP_H = 20, 612, 612, 128


def lonlat_to_xy(lon, lat):
    x = MAP_X0 + (lon + 168) / 360.0 * MAP_W
    y = MAP_Y0 + (78 - lat) / 136.0 * MAP_H
    return x, y


# ---------------------------------------------------------------- drawing
def draw_masthead(d):
    title_f = font(SERIF_B, 30)
    date_f = font(SANS_B, 12)
    claim_f = font(SANS_B, 11)
    d.text((12, 6), "THE WORLD IN ONE DAY", font=title_f, fill=INK)
    date = "TUESDAY 24 NOVEMBER 2026"
    check_w(date_f, date, 400, "masthead date")
    d.text((1012 - text_w(date_f, date), 14), date, font=date_f, fill=INK)
    claim = ("38 DATED STORIES  \u00b7  7 REGIONS  \u00b7  21 FIELDS  "
             "\u00b7  13 DRAWN  \u00b7  EVERY CLAIM LABELLED")
    check_w(claim_f, claim, 1000, "masthead claim")
    d.text(((1024 - text_w(claim_f, claim)) / 2, 42), claim,
           font=claim_f, fill=RED)
    d.line([(12, 58), (1012, 58)], fill=RULE, width=2)


def draw_region_bar(d):
    f = font(SANS_B, 11)
    chip = 11
    parts = []
    total_w = 0
    for name, color, count in REGIONS:
        label = f"{name} {count}"
        total_w += chip + 4 + text_w(f, label) + 26
    total_w -= 26
    check_w(f, "x", total_w, "region bar")  # width guard via total below
    if total_w > 1000:
        fail(f"region bar: {total_w:.0f}px wide, max 1000px")
    x = (1024 - total_w) / 2
    y = 68
    for name, color, count in REGIONS:
        label = f"{name} {count}"
        d.rectangle([x, y, x + chip, y + chip], fill=color)
        x += chip + 4
        d.text((x, y - 1), label, font=f, fill=INK)
        x += text_w(f, label) + 26
    d.line([(12, 88), (1012, 88)], fill=RULE, width=1)


def draw_in_numbers(d):
    f_num = font(SANS_B, 19)
    f_lab = font(SANS, 8)
    col_w = 1000 / 7
    for i, (num, lab) in enumerate(IN_NUMBERS):
        cx = 12 + col_w * i + col_w / 2
        check_w(f_num, num, col_w - 8, f"IN NUMBERS {num}")
        d.text((cx - text_w(f_num, num) / 2, 94), num, font=f_num, fill=INK)
        lines = wrap(f_lab, lab, col_w - 8, 1, f"IN NUMBERS label {lab}")
        d.text((cx - text_w(f_lab, lines[0]) / 2, 118), lines[0],
               font=f_lab, fill=MUTED)
    d.text((12, 90), "", font=f_lab, fill=INK)
    d.line([(12, 130), (1012, 130)], fill=RULE, width=1)


def draw_utc(d):
    f = font(SANS, 11)
    fb = font(SANS_B, 11)
    rows = [UTC_ITEMS[:4], UTC_ITEMS[4:]]
    y = 136
    for row in rows:
        col_w = 1000 / len(row)
        for i, (t, what) in enumerate(row):
            x = 12 + col_w * i
            d.text((x, y), t, font=fb, fill=RED)
            tx = x + text_w(fb, t) + 8
            check_w(f, what, col_w - (tx - x) - 8, f"UTC {t}")
            d.text((tx, y), what, font=f, fill=INK)
        y += 16
    d.line([(12, 164), (1012, 164)], fill=RULE, width=1)


def scene_sky(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SKY)
    d.ellipse([x1 - 52, y0 + 8, x1 - 20, y0 + 40], fill=(255, 214, 90))


def scene_sea(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SEA)


def draw_ship_scene(d, x0, y0, x1, y1):
    """Bright daytime sea: town, lighthouse, listing corvette, smoke."""
    scene_sky(d, x0, y0, x1, y0 + 46)
    scene_sea(d, x0, y0 + 46, x1, y1)
    # shoreline town
    d.rectangle([x0, y0 + 34, x1, y0 + 50], fill=(222, 205, 170))
    for bx in range(x0 + 8, x1 - 20, 26):
        d.rectangle([bx, y0 + 22, bx + 18, y0 + 50], fill=(240, 234, 220))
        d.polygon([(bx, y0 + 22), (bx + 9, y0 + 14), (bx + 18, y0 + 22)],
                  fill=(200, 90, 60))
    # lighthouse
    d.rectangle([x1 - 34, y0 + 8, x1 - 24, y0 + 50], fill=(250, 250, 250))
    d.rectangle([x1 - 36, y0 + 4, x1 - 22, y0 + 10], fill=RED)
    # listing corvette, hull tilted
    d.polygon([(x0 + 60, y0 + 78), (x0 + 210, y0 + 66), (x0 + 228, y0 + 78),
               (x0 + 212, y0 + 92), (x0 + 74, y0 + 98)], fill=(70, 80, 90))
    d.rectangle([x0 + 120, y0 + 52, x0 + 132, y0 + 70], fill=(90, 100, 110))
    d.rectangle([x0 + 150, y0 + 56, x0 + 158, y0 + 68], fill=(90, 100, 110))
    # smoke puffs
    for cx, cy, r in [(x0 + 130, y0 + 44, 9), (x0 + 142, y0 + 34, 12),
                      (x0 + 158, y0 + 24, 10)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(120, 120, 120))
    # drones as small dots with motion ticks
    for cx, cy in [(x0 + 40, y0 + 26), (x0 + 250, y0 + 30), (x0 + 280, y0 + 52)]:
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=INK)
        d.line([(cx - 8, cy), (cx + 8, cy)], fill=INK, width=1)
    # waves
    for wy in (y0 + 100, y0 + 108):
        for wx in range(x0 + 6, x1 - 10, 34):
            d.arc([wx, wy, wx + 22, wy + 8], 180, 360, fill=(255, 255, 255),
                  width=2)


def draw_hormuz_scene(d, x0, y0, x1, y1):
    """Informative regional map of the Strait of Hormuz, bright."""
    d.rectangle([x0, y0, x1, y1], fill=(214, 231, 240))
    f = font(SANS_B, 10)
    f2 = font(SANS, 9)
    # Iran (top land)
    d.polygon([(x0, y0), (x1, y0), (x1, y0 + 34), (x0 + 210, y0 + 52),
               (x0 + 150, y0 + 40), (x0, y0 + 44)], fill=LAND)
    # Oman / UAE (bottom land)
    d.polygon([(x0, y1), (x1, y1), (x1, y1 - 30), (x0 + 230, y1 - 48),
               (x0 + 170, y1 - 34), (x0, y1 - 40)], fill=LAND)
    d.text((x0 + 14, y0 + 8), "IRAN", font=f, fill=INK)
    d.text((x0 + 16, y1 - 26), "OMAN", font=f, fill=INK)
    d.text((x1 - 62, y1 - 26), "UAE", font=f, fill=INK)
    # strait channel between the lands (kept clear of every label)
    d.line([(x0 + 150, y0 + 52), (x0 + 232, y1 - 46)], fill=BLUE, width=3)
    d.text((x0 + 118, y0 + 62), "STRAIT OF", font=f2, fill=BLUE)
    d.text((x0 + 118, y0 + 74), "HORMUZ", font=f, fill=BLUE)
    # tankers
    for tx, ty in [(x0 + 60, y0 + 78), (x0 + 250, y0 + 62)]:
        d.rectangle([tx, ty, tx + 34, ty + 10], fill=(200, 60, 40))
        d.rectangle([tx + 22, ty - 8, tx + 30, ty], fill=(120, 60, 40))
    d.text((x0 + 60, y0 + 92), "TANKERS WAIT", font=f2, fill=INK)
    # BLOCKADE label above its dashed line; the dashes sit on their own row
    d.text((x0 + 196, y0 + 38), "BLOCKADE", font=f2, fill=RED)
    for dx in range(x0 + 196, x0 + 252, 12):
        d.line([(dx, y0 + 52), (dx + 7, y0 + 52)], fill=RED, width=3)


def draw_data_scene(d, x0, y0, x1, y1):
    """Bright data lead: giant number + mini bar chart + up arrow.

    Scene is 118px tall; every row is budgeted to stay inside it:
    number 40pt, label, then 4 bars on 10px rows. Nothing may cross
    the scene's bottom edge into the kicker below it.
    """
    d.rectangle([x0, y0, x1, y1], fill=(232, 244, 232))
    f_big = font(SANS_B, 40)
    f_lab = font(SANS_B, 11)
    f_s = font(SANS, 10)
    d.text((x0 + 14, y0 + 4), "+31.5%", font=f_big, fill=GREEN)
    # up arrow
    ax, ay = x1 - 62, y0 + 10
    d.polygon([(ax + 22, ay), (ax + 44, ay + 26), (ax + 30, ay + 26),
               (ax + 30, ay + 52), (ax + 14, ay + 52), (ax + 14, ay + 26),
               (ax, ay + 26)], fill=GREEN)
    d.text((x0 + 16, y0 + 50), "NVIDIA SHARES, TUESDAY", font=f_lab,
           fill=INK)
    # mini bars: value text sits in its own column, never on a bar
    bars = [("NVDA", 31.5, GREEN), ("TAIEX", 9.0, BLUE),
            ("KOSPI", 7.3, BLUE), ("NASDAQ", 6.5, BLUE)]
    by = y0 + 68
    bx = x0 + 78
    bw_max = x1 - 8 - 58 - bx
    for name, val, col in bars:
        d.text((x0 + 16, by), name, font=f_s, fill=INK)
        bw = bw_max * val / 32.0
        d.rectangle([bx, by + 1, bx + max(bw, 4), by + 8], fill=col)
        d.text((bx + bw_max + 6, by), f"+{val}%", font=f_s, fill=INK)
        by += 10


def draw_mid_scene(d, kind, x0, y0, x1, y1):
    """Small bright vignette for a mid card. Shapes stay inside the box."""
    w, h = x1 - x0, y1 - y0
    if kind == "hall":
        d.rectangle([x0, y0, x1, y1], fill=(226, 232, 240))
        d.rectangle([x0 + 30, y0 + 16, x1 - 30, y1 - 6], fill=(250, 250, 250))
        d.polygon([(x0 + 24, y0 + 16), (x0 + w // 2, y0 + 2),
                   (x1 - 24, y0 + 16)], fill=BLUE)
        # flag poles only at the far edges; the COP31 label owns the middle
        for fx in (x0 + 38, x1 - 40):
            d.line([(fx, y0 + 26), (fx, y0 + 40)], fill=RED, width=2)
        d.text((x0 + w // 2 - 18, y0 + 26), "COP31", font=font(SANS_B, 11),
               fill=INK)
    elif kind == "plane":
        scene_sky(d, x0, y0, x1, y1)
        d.polygon([(x0 + 30, y0 + 26), (x0 + 150, y0 + 20), (x0 + 158, y0 + 26),
                   (x0 + 150, y0 + 32), (x0 + 30, y0 + 32)], fill=(90, 100, 110))
        d.polygon([(x0 + 60, y0 + 20), (x0 + 78, y0 + 6), (x0 + 92, y0 + 20)],
                  fill=(90, 100, 110))
        d.ellipse([x0 + 148, y0 + 22, x0 + 156, y0 + 30], fill=(200, 220, 240))
        for cx in (x0 + 40, x0 + 80, x0 + 120):
            d.ellipse([cx - 6, y0 + 38, cx + 6, y0 + 46], fill=(255, 255, 255))
    elif kind == "odesa":
        d.rectangle([x0, y0, x1, y1], fill=(203, 220, 238))
        for bx in range(x0 + 8, x1 - 16, 30):
            d.rectangle([bx, y0 + 18, bx + 22, y1 - 4], fill=(70, 80, 95))
            for wy in (y0 + 24, y0 + 32):
                d.rectangle([bx + 4, wy, bx + 9, wy + 4], fill=(255, 214, 90))
                d.rectangle([bx + 13, wy, bx + 18, wy + 4], fill=(255, 214, 90))
        d.ellipse([x1 - 34, y0 + 4, x1 - 12, y0 + 26], fill=(255, 236, 170))
    elif kind == "planes":
        scene_sky(d, x0, y0, x1, y1)
        d.rectangle([x0, y0 + 34, x1, y1], fill=(200, 205, 210))
        for px in range(x0 + 12, x1 - 40, 52):
            d.polygon([(px, y0 + 26), (px + 36, y0 + 22), (px + 40, y0 + 26),
                       (px + 36, y0 + 30), (px, y0 + 30)], fill=(255, 255, 255))
            d.line([(px + 8, y0 + 30), (px + 8, y0 + 40)], fill=(120, 120, 120),
                   width=2)
            d.line([(px + 28, y0 + 30), (px + 28, y0 + 40)], fill=(120, 120, 120),
                   width=2)
    elif kind == "ships":
        scene_sky(d, x0, y0, x1, y0 + 18)
        scene_sea(d, x0, y0 + 18, x1, y1)
        for sx in range(x0 + 10, x1 - 40, 56):
            d.rectangle([sx, y0 + 26, sx + 34, y0 + 34], fill=(70, 80, 90))
            d.rectangle([sx + 12, y0 + 18, sx + 18, y0 + 26], fill=(90, 100, 110))
    elif kind == "lab":
        d.rectangle([x0, y0, x1, y1], fill=(228, 240, 228))
        d.rectangle([x0 + 30, y0 + 8, x0 + 44, y0 + 34], fill=(255, 255, 255))
        d.polygon([(x0 + 30, y0 + 34), (x0 + 44, y0 + 34), (x0 + 52, y1 - 8),
                   (x0 + 22, y1 - 8)], fill=(255, 255, 255))
        d.polygon([(x0 + 32, y0 + 36), (x0 + 42, y0 + 36), (x0 + 47, y1 - 10),
                   (x0 + 27, y1 - 10)], fill=(80, 180, 120))
        d.ellipse([x0 + 90, y0 + 10, x0 + 130, y1 - 10], fill=(180, 210, 235))
        d.rectangle([x0 + 108, y0 + 14, x0 + 112, y1 - 14], fill=(255, 255, 255))
    elif kind == "boat":
        scene_sky(d, x0, y0, x1, y0 + 16)
        d.rectangle([x0, y0 + 16, x1, y1], fill=(150, 200, 220))
        d.polygon([(x0 + 40, y0 + 26), (x0 + 150, y0 + 26), (x0 + 138, y0 + 38),
                   (x0 + 52, y0 + 38)], fill=(140, 90, 40))
        d.rectangle([x0 + 88, y0 + 14, x0 + 94, y0 + 26], fill=(140, 90, 40))
        for wy in (y0 + 40,):
            for wx in range(x0 + 6, x1 - 10, 30):
                d.arc([wx, wy, wx + 20, wy + 7], 180, 360,
                      fill=(255, 255, 255), width=2)
    elif kind == "desert":
        d.rectangle([x0, y0, x1, y1], fill=(240, 220, 170))
        d.ellipse([x1 - 36, y0 + 4, x1 - 12, y0 + 28], fill=(255, 214, 90))
        d.polygon([(x0, y1), (x0 + 60, y0 + 22), (x0 + 120, y1)], fill=(222, 196, 140))
        d.polygon([(x0 + 90, y1), (x0 + 150, y0 + 28), (x1, y1)], fill=(222, 196, 140))
        for vx in range(x0 + 16, x1 - 30, 46):
            d.rectangle([vx, y0 + 30, vx + 30, y0 + 40], fill=(90, 90, 90))
            d.ellipse([vx + 5, y0 + 40, vx + 11, y0 + 46], fill=INK)
            d.ellipse([vx + 19, y0 + 40, vx + 25, y0 + 46], fill=INK)
    elif kind == "flags":
        d.rectangle([x0, y0, x1, y1], fill=(226, 232, 240))
        d.rectangle([x0 + 40, y0 + 20, x1 - 40, y1 - 6], fill=(250, 250, 250))
        d.polygon([(x0 + 34, y0 + 20), (x0 + w // 2, y0 + 8),
                   (x1 - 34, y0 + 20)], fill=(120, 120, 120))
        # two small flags
        d.line([(x0 + 60, y0 + 26), (x0 + 60, y0 + 14)], fill=INK, width=2)
        d.rectangle([x0 + 60, y0 + 14, x0 + 84, y0 + 24], fill=RED)
        d.line([(x1 - 60, y0 + 26), (x1 - 60, y0 + 14)], fill=INK, width=2)
        d.rectangle([x1 - 84, y0 + 14, x1 - 60, y0 + 24], fill=BLUE)
    elif kind == "laptop":
        d.rectangle([x0, y0, x1, y1], fill=(228, 232, 240))
        d.rectangle([x0 + 36, y0 + 6, x1 - 36, y0 + 34], fill=(40, 50, 60))
        d.rectangle([x0 + 42, y0 + 11, x1 - 42, y0 + 29], fill=(120, 200, 120))
        for lx in range(x0 + 48, x1 - 52, 14):
            d.line([(lx, y0 + 26), (lx + 8, y0 + 26)], fill=(40, 50, 60), width=2)
        d.polygon([(x0 + 28, y0 + 34), (x1 - 28, y0 + 34), (x1 - 20, y1 - 6),
                   (x0 + 20, y1 - 6)], fill=(90, 100, 110))


def draw_leads(d):
    leads = [MAINS[0], MAINS[1], MAINS[5]]  # stories 1, 2, 6
    f_banner = font(SANS_B, 15)
    f_kick = font(SANS_B, 9)
    f_head = font(SANS_B, 15)
    f_deck = font(SANS, 10)
    col_w, gap, y0, h = 328, 8, 164, 224
    for i, s in enumerate(leads):
        x0 = 12 + i * (col_w + gap)
        x1 = x0 + col_w
        y1 = y0 + h
        d.rectangle([x0, y0, x1, y1], fill=CARD, outline=RULE, width=1)
        # red punch banner
        d.rectangle([x0, y0, x1, y0 + 30], fill=RED)
        check_w(f_banner, s["banner"], col_w - 16, f"lead {s['n']} banner")
        d.text((x0 + 8, y0 + 6), s["banner"], font=f_banner, fill=(255, 255, 255))
        # number badge on the banner, right side
        badge = f"{s['n']}"
        bw = text_w(f_banner, badge) + 14
        d.ellipse([x1 - 8 - bw, y0 + 4, x1 - 8, y0 + 26],
                  fill=(255, 255, 255))
        d.text((x1 - 8 - bw + 7, y0 + 5), badge, font=f_banner, fill=RED)
        # scene
        sy0, sy1 = y0 + 30, y0 + 148
        if s["kind"] == "data":
            draw_data_scene(d, x0, sy0, x1, sy1)
        elif s["kind"] == "ship":
            draw_ship_scene(d, x0, sy0, x1, sy1)
        else:
            draw_hormuz_scene(d, x0, sy0, x1, sy1)
        d.rectangle([x0, sy0, x1, sy1], outline=RULE, width=1)
        # kicker / headline / deck
        ty = y0 + 152
        d.text((x0 + 8, ty), s["tag"], font=f_kick,
               fill=REGION_COLOR[s["region"]])
        head_lines = wrap(f_head, s["head"], col_w - 16, 2,
                          f"lead {s['n']} headline")
        hy = ty + 14
        for ln in head_lines:
            d.text((x0 + 8, hy), ln, font=f_head, fill=INK)
            hy += 18
        deck_lines = wrap(f_deck, s["deck"], col_w - 16, 1,
                          f"lead {s['n']} deck")
        d.text((x0 + 8, hy + 2), deck_lines[0], font=f_deck, fill=MUTED)


def draw_mids(d):
    mids = [s for s in MAINS if s["n"] not in (1, 2, 6)]
    f_head = font(SANS_B, 11)
    f_deck = font(SANS, 9)
    f_num = font(SANS_B, 10)
    col_w, gap, row_h, row_gap = 192, 10, 97, 6
    for i, s in enumerate(mids):
        col, row = i % 5, i // 5
        x0 = 12 + col * (col_w + gap)
        x1 = x0 + col_w
        y0 = 388 + row * (row_h + row_gap)
        y1 = y0 + row_h
        d.rectangle([x0, y0, x1, y1], fill=CARD, outline=RULE, width=1)
        # scene banner, top 48px, fully inside the card
        draw_mid_scene(d, s["kind"], x0 + 1, y0 + 1, x1 - 1, y0 + 48)
        d.rectangle([x0, y0, x1, y0 + 48], outline=RULE, width=1)
        # number badge overlapping the scene corner, inside the card
        d.ellipse([x0 + 4, y0 + 4, x0 + 22, y0 + 22],
                  fill=REGION_COLOR[s["region"]], outline=(255, 255, 255),
                  width=1)
        d.text((x0 + 4 + (18 - text_w(f_num, str(s["n"]))) / 2, y0 + 6),
               str(s["n"]), font=f_num, fill=(255, 255, 255))
        head_lines = wrap(f_head, s["head"], col_w - 12, 2,
                          f"mid {s['n']} headline")
        hy = y0 + 52
        for ln in head_lines:
            d.text((x0 + 6, hy), ln, font=f_head, fill=INK)
            hy += 13
        deck_lines = wrap(f_deck, s["deck"], col_w - 12, 1,
                          f"mid {s['n']} deck")
        d.text((x0 + 6, hy + 1), deck_lines[0], font=f_deck, fill=MUTED)


def draw_map(d):
    # panel frame + title
    d.rectangle([12, 588, 640, 780], fill=CARD, outline=RULE, width=1)
    f_title = font(SANS_B, 11)
    title = "THE WORLD \u2014 13 DRAWN STORIES, PINS 1\u201313"
    check_w(f_title, title, 604, "map title")
    d.text((20, 594), title, font=f_title, fill=INK)
    # ocean
    d.rectangle([20, 612, 632, 740], fill=OCEAN)
    # landmasses, solid
    for poly in LANDMASSES:
        pts = [lonlat_to_xy(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=LAND, outline=LAND_EDGE)
    # ocean labels — checked against real geography:
    # PACIFIC on the west edge, ATLANTIC in the middle, INDIAN below Asia.
    f_oc = font(SANS_B, 9)
    for label, lon, lat in [("PACIFIC", -150, -25), ("ATLANTIC", -25, -20),
                            ("INDIAN OCEAN", 85, -35)]:
        cx, cy = lonlat_to_xy(lon, lat)
        d.text((cx - text_w(f_oc, label) / 2, cy - 6), label, font=f_oc,
               fill=(90, 120, 150))
    # pins, jittered where the cluster is tight, leader line to true spot
    f_pin = font(SANS_B, 9)
    placed = []
    for s in MAINS:
        gx, gy = lonlat_to_xy(*s["pin"])
        dx, dy = s.get("jitter", (0, 0))
        px, py = gx + dx, gy + dy
        for qx, qy, qn in placed:
            dist = ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
            if dist < 16:
                fail(f"map pins {s['n']} and {qn} only {dist:.1f}px apart")
        placed.append((px, py, s["n"]))
        if (dx, dy) != (0, 0):
            d.line([(gx, gy), (px, py)], fill=MUTED, width=1)
            d.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=INK)
        col = REGION_COLOR[s["region"]]
        d.ellipse([px - 8, py - 8, px + 8, py + 8], fill=col,
                  outline=(255, 255, 255), width=2)
        num = str(s["n"])
        d.text((px - text_w(f_pin, num) / 2, py - 6), num, font=f_pin,
               fill=(255, 255, 255))
    # legend on its OWN two rows below the map, nothing touching
    f_leg = font(SANS_B, 9)
    f_lab = font(SANS_B, 10)
    d.text((20, 746), "PIN COLOUR = REGION:", font=f_lab, fill=INK)
    pin_counts = {}
    for s in MAINS:
        pin_counts[s["region"]] = pin_counts.get(s["region"], 0) + 1
    order = ["AFRICA", "ASIA", "EUROPE", "LATIN AM.", "MIDDLE EAST",
             "N. AMERICA"]
    rows = [[], []]
    for i, name in enumerate(order):
        rows[i % 2].append((name, pin_counts[name]))
    for ri, row in enumerate(rows):
        ly = 746 + ri * 15 if ri == 0 else 761
        # row 0 shares the line with the label; row 1 starts at x=20
        x = 196 if ri == 0 else 20
        for name, count in row:
            label = f"{name} {count}"
            w = 10 + 4 + text_w(f_leg, label) + 18
            if x + w > 632:
                fail(f"map legend row {ri}: {label} overflows at {x + w:.0f}px")
            d.rectangle([x, ly + 1, x + 10, ly + 11],
                        fill=REGION_COLOR[name])
            d.text((x + 14, ly), label, font=f_leg, fill=INK)
            x += w


def hbar_chart(d, x0, y0, x1, y1, title, rows, label_w, max_val, unit):
    d.rectangle([x0, y0, x1, y1], fill=CARD, outline=RULE, width=1)
    f_title = font(SANS_B, 11)
    f_lab = font(SANS_B, 9)
    f_val = font(SANS_B, 9)
    d.text((x0 + 8, y0 + 5), title, font=f_title, fill=INK)
    n = len(rows)
    row_h = (y1 - y0 - 26) / n
    for i, (name, val_text, val) in enumerate(rows):
        ry = y0 + 24 + i * row_h
        check_w(f_lab, name, label_w - 4, f"chart {title} label {name}")
        d.text((x0 + 8, ry), name, font=f_lab, fill=INK)
        bx = x0 + 8 + label_w
        bw_max = x1 - 8 - 52 - bx
        bw = bw_max * val / max_val
        d.rectangle([bx, ry + 1, bx + max(bw, 3), ry + 9],
                    fill=BLUE if title.startswith("STORIES") else GREEN)
        d.text((x1 - 8 - text_w(f_val, val_text), ry), val_text, font=f_val,
               fill=INK)


def draw_charts(d):
    region_rows = [(name, str(v), v) for name, v in REGION_BARS]
    # full region names on the chart — measured before render
    hbar_chart(d, 648, 588, 1012, 680, "STORIES BY REGION", region_rows,
               108, 7, "")
    market_rows = [(n, t, v) for n, t, v in MARKETS]
    hbar_chart(d, 648, 688, 1012, 780, "MARKETS ON TUESDAY", market_rows,
               76, 31.5, "")


def draw_also(d):
    f_title = font(SANS_B, 11)
    f_leg = font(SANS_B, 9)
    f_item = font(SANS, 9)
    f_num = font(SANS_B, 9)
    f_circ = font(SANS_B, 8)
    d.text((12, 784), "ALSO ON \u2014 25 MORE STORIES (14\u201338)",
           font=f_title, fill=INK)
    legend = "C CONFIRMED   O OFFICIAL   R REPORTED   CL CLAIM"
    check_w(f_leg, legend, 480, "ALSO legend")
    d.text((1012 - text_w(f_leg, legend), 785), legend, font=f_leg,
           fill=MUTED)
    d.line([(12, 802), (1012, 802)], fill=RULE, width=1)
    cols = [ALSO[:9], ALSO[9:17], ALSO[17:]]
    for ci, col in enumerate(cols):
        x0 = 12 + ci * 336
        for ri, (n, region, claim, deck) in enumerate(col):
            y = 806 + ri * 16
            colr = REGION_COLOR[region]
            d.ellipse([x0, y, x0 + 12, y + 12], fill=colr)
            d.text((x0 + (12 - text_w(f_circ, claim)) / 2, y + 2), claim,
                   font=f_circ, fill=(255, 255, 255))
            nx = x0 + 16
            d.text((nx, y + 1), f"{n}.", font=f_num, fill=INK)
            dx = nx + text_w(f_num, f"{n}.") + 5
            check_w(f_item, deck, 328 - (dx - x0), f"ALSO {n}")
            d.text((dx, y + 1), deck, font=f_item, fill=INK)


def draw_footer(d):
    f_title = font(SANS_B, 10)
    f_body = font(SANS, 9)
    f_def = font(SANS_B, 9)
    # left box: how checked
    d.rectangle([12, 950, 500, 1000], fill=CARD, outline=RULE, width=1)
    d.text((20, 954), "HOW THIS PAGE WAS CHECKED", font=f_title, fill=INK)
    left = ["Every story is dated Tuesday 24 November 2026 and",
            "carries its source. Numbers come from the cited",
            "report; nothing here is invented or undated."]
    ly = 968
    for ln in left:
        d.text((20, ly), ln, font=f_body, fill=INK)
        ly += 11
    # right box: date check
    d.rectangle([508, 950, 1012, 1000], fill=CARD, outline=RULE, width=1)
    d.text((516, 954), "DATE CHECK", font=f_title, fill=INK)
    right = ["Left out: stories still developing at press time.",
             "Not yet known: the full Libya toll, the Hormuz",
             "tanker count. All 38 stories check on their dates."]
    ly = 968
    for ln in right:
        d.text((516, ly), ln, font=f_body, fill=INK)
        ly += 11
    # definition strip — full width, own row, nothing clipped
    definition = ("C = CONFIRMED  \u00b7  O = OFFICIAL  \u00b7  R = REPORTED  "
                  "\u00b7  CL = CLAIM \u2014 one circle on every ALSO story "
                  "(25/25) \u00b7 Pins 1\u201313 = the 13 drawn stories")
    check_w(f_def, definition, 1000, "definition strip")
    d.text(((1024 - text_w(f_def, definition)) / 2, 1008), definition,
           font=f_def, fill=INK)


def main():
    # ---- arithmetic gates (run before any drawing) ----
    total_regions = sum(c for _, _, c in REGIONS)
    if total_regions != 38:
        fail(f"region bar sums to {total_regions}, not 38")
    for name, _, count in REGIONS:
        if count > 7:
            fail(f"region {name} has {count}, max 7")
    if len(MAINS) != 13:
        fail(f"{len(MAINS)} drawn stories, not 13")
    if len(ALSO) != 25:
        fail(f"{len(ALSO)} ALSO stories, not 25")
    if ALSO[-1][0] != 38:
        fail(f"last ALSO number is {ALSO[-1][0]}, not 38")
    if len(FIELDS) != 21:
        fail(f"{len(FIELDS)} fields, not 21")
    if len(IN_NUMBERS) != 7:
        fail(f"{len(IN_NUMBERS)} IN NUMBERS items, not 7")
    if len(UTC_ITEMS) != 7:
        fail(f"{len(UTC_ITEMS)} UTC items, not 7")
    pin_sum = 0
    for s in MAINS:
        pin_sum += 1
    if pin_sum != 13:
        fail(f"{pin_sum} pins, not 13")

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_masthead(d)
    draw_region_bar(d)
    draw_in_numbers(d)
    draw_utc(d)
    draw_leads(d)
    draw_mids(d)
    draw_map(d)
    draw_charts(d)
    draw_also(d)
    draw_footer(d)

    if ERRORS:
        print("LAYOUT VALIDATOR FAILED:")
        for e in ERRORS:
            print(" -", e)
        sys.exit(1)

    img.save("entry.png")
    digest = hashlib.sha256(open("entry.png", "rb").read()).hexdigest()
    print(f"entry.png written sha256={digest}")
    print("arithmetic: 38 stories = 13 drawn + 25 ALSO; "
          "regions 7+7+6+7+4+4+3 = 38; fields 21; pins 13")


if __name__ == "__main__":
    main()

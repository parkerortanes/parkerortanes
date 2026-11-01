"""Build assets/banner.svg (the terminal-style banner) from profile.yml.

Called by update_readme.py on every run, so the banner always matches
the dates and news in profile.yml. Nothing in here needs hand-editing.
"""
import random
from datetime import date, datetime
from html import escape

W, H = 1200, 300
AMBER, WHITE, DIM, GREEN, BG = "#ffa028", "#e8e8e8", "#7a7a7a", "#3ad13a", "#0a0a0a"
MONO = "Consolas, Menlo, 'DejaVu Sans Mono', monospace"
CHAR_W = 9.6          # width of one 16px monospace character (forced via textLength)
TICKER_SPEED = 55     # pixels per second


def _d(v):
    if v in (None, ""):
        return None
    return v if isinstance(v, date) else datetime.strptime(str(v), "%Y-%m-%d").date()


def _status(item, today):
    start, end = _d(item.get("start")), _d(item.get("end"))
    if start and today < start:
        return "upcoming"
    if end and today > end:
        return "past"
    return "current"


def _name(item, key):
    """Use the optional `short:` name on the banner if one is given."""
    return item.get("short") or item[key]


def _rows(p, today):
    """The label/value lines under the name, picked by today's date."""
    rows = []
    for e in p.get("experience", []):
        s = _status(e, today)
        if s == "current":
            rows.append(("ROLE", f"{e['role']} · {_name(e, 'org')}"))
        elif s == "upcoming":
            rows.append(("INCOMING", f"{e['role']} · {_name(e, 'org')} · {_d(e['start']):%b %Y}"))
    for ed in p.get("education", []):
        s = _status(ed, today)
        if s == "current":
            rows.append(("SCHOOL", _name(ed, "school")))
        elif s == "upcoming":
            rows.append(("NEXT", f"{_name(ed, 'school')} · {_d(ed['start']):%b %Y}"))
    if p.get("location"):
        rows.append(("LOC", p["location"]))
    return rows[:4]


def _ticker_items(p, today):
    news = sorted(p.get("news", []), key=lambda n: _d(n["date"]), reverse=True)[:3]
    items = [f"{_d(n['date']):%b %Y}: {n['text']}" for n in news]
    items += [value for _, value in _rows(p, today) if value != p.get("location")]
    if p.get("skills"):
        items.append(" · ".join(p["skills"]))
    return [i.upper() for i in items]


def _chart(today, x0, y0, w, h):
    """A random-walk 'price' line. Seeded by the date, so it changes daily
    but stays the same within a day. Always ends higher than it starts."""
    rng = random.Random(today.toordinal())
    n, v, walk = 90, 0.0, []
    for _ in range(n):
        v += rng.gauss(0, 1.0)
        walk.append(v)
    # Pin the end back to the start (keeps the bumps), then tilt upward,
    # so every day's chart ends higher than it began.
    bridge = [w - walk[-1] * i / (n - 1) for i, w in enumerate(walk)]
    rise = 1.5 * (max(bridge) - min(bridge))
    pts = [b + rise * i / (n - 1) for i, b in enumerate(bridge)]
    lo, hi = min(pts), max(pts)
    xy = [(x0 + i * w / (n - 1), y0 + h - (val - lo) / (hi - lo or 1) * h) for i, val in enumerate(pts)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in xy), xy[-1]


def _ticker_text(x, body, length):
    return (f'<text xml:space="preserve" x="{x}" y="285" textLength="{length:.0f}" '
            f'lengthAdjust="spacingAndGlyphs">{body}</text>')


def build_svg(p, today):
    ticker = p.get("ticker", "PRKR")
    name = escape(p["name"].upper())
    rows = _rows(p, today)

    # ── ticker tape: repeat items until one loop is wider than the banner
    items = _ticker_items(p, today)
    plain, body = "", ""
    while len(plain) * CHAR_W < W + 100:
        for it in items:
            plain += f"   ▲ {it}"
            body += f'   <tspan fill="{GREEN}">▲</tspan> {escape(it)}'
    loop = len(plain) * CHAR_W
    secs = loop / TICKER_SPEED

    # ── chart panel (right side)
    cx, cy, cw, ch = 760, 70, 400, 150
    line, (lx, ly) = _chart(today, cx, cy, cw, ch)
    grid = "".join(
        f'<line x1="{cx}" x2="{cx + cw}" y1="{cy + i * ch / 4:.0f}" y2="{cy + i * ch / 4:.0f}" '
        f'stroke="#2a2a2a" stroke-dasharray="2 4"/>' for i in range(5))

    row_svg = "".join(
        f'<text x="40" y="{168 + i * 24}"><tspan fill="{AMBER}">{label}</tspan>'
        f'<tspan x="140" fill="{WHITE}">{escape(value)}</tspan></text>'
        for i, (label, value) in enumerate(rows))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(p['name'])}: {escape(p.get('tagline', ''))}">
  <style>
    text {{ font-family: {MONO}; }}
    .line {{ stroke-dasharray: 2000; stroke-dashoffset: 2000; animation: draw 2.5s ease-out forwards; }}
    .tape {{ animation: scroll {secs:.0f}s linear infinite; }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
    @keyframes scroll {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-{loop:.0f}px); }} }}
  </style>
  <rect width="{W}" height="{H}" fill="{BG}"/>

  <!-- top bar -->
  <rect width="{W}" height="30" fill="{AMBER}"/>
  <text x="14" y="21" font-size="15" font-weight="700" fill="#000">{ticker} US &lt;Equity&gt;  DES</text>
  <text x="{W - 14}" y="21" font-size="15" fill="#000" text-anchor="end">{today:%d %b %Y}</text>

  <!-- name + details -->
  <text x="38" y="92" font-size="46" font-weight="700" fill="{WHITE}">{name}</text>
  <text x="40" y="124" font-size="17" fill="{DIM}">{escape(p.get('tagline', ''))}</text>
  <line x1="40" x2="700" y1="142" y2="142" stroke="#2a2a2a"/>
  <g font-size="16">{row_svg}</g>

  <!-- chart -->
  <text x="{cx}" y="58" font-size="13" fill="{AMBER}">{ticker} · 1Y</text>
  {grid}
  <polyline class="line" points="{line}" fill="none" stroke="{WHITE}" stroke-width="1.5"/>
  <circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="{AMBER}"/>

  <!-- ticker tape -->
  <rect y="258" width="{W}" height="42" fill="#000"/>
  <line x1="0" x2="{W}" y1="258" y2="258" stroke="{AMBER}"/>
  <g class="tape" font-size="16" fill="{AMBER}">
    {_ticker_text(0, body, loop)}
    {_ticker_text(loop, body, loop)}
  </g>
</svg>
"""


def write_banner(p, path, today=None):
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_svg(p, today or date.today()), encoding="utf-8")

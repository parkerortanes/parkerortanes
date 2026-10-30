#!/usr/bin/env python3
"""Rebuild README.md from profile.yml + live GitHub activity.

Only the text between <!-- START:x --> and <!-- END:x --> markers is
replaced, so anything you hand-write elsewhere in README.md is kept.

Usage:  python update_readme.py            (normal run, calls GitHub API)
        python update_readme.py --offline  (skip GitHub API, for testing)
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
README = ROOT / "README.md"
PROFILE = ROOT / "profile.yml"
NEW_BADGE_DAYS = 45
TODAY = date.today()


# ── helpers ──────────────────────────────────────────────────
def to_date(v):
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v), "%Y-%m-%d").date()


def fmt_month(d):
    return d.strftime("%b %Y") if d else "Present"


def status(item):
    """'upcoming', 'current', or 'past' relative to today."""
    start, end = to_date(item.get("start")), to_date(item.get("end"))
    if start and TODAY < start:
        return "upcoming"
    if end and TODAY > end:
        return "past"
    return "current"


def replace_section(text, name, body):
    pattern = re.compile(
        rf"(<!-- START:{name} -->)(.*?)(<!-- END:{name} -->)", re.DOTALL
    )
    if not pattern.search(text):
        print(f"warning: no markers for '{name}' in README.md, skipping")
        return text
    return pattern.sub(lambda m: f"{m.group(1)}\n{body.strip()}\n{m.group(3)}", text)


# ── GitHub API ───────────────────────────────────────────────
def gh(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def github_activity(user):
    repos = gh(f"/users/{user}/repos?sort=pushed&per_page=30&type=owner")
    repos = [r for r in repos if not r["fork"] and r["name"].lower() != user.lower()]
    events = gh(f"/users/{user}/events/public?per_page=100")
    return repos, events


# ── section builders ─────────────────────────────────────────
def build_header(p):
    links = " · ".join(f"[{k}]({v})" for k, v in (p.get("links") or {}).items())
    lines = [f"# Hi, I'm {p['name']} 👋", "", f"**{p['tagline']}**"]
    if p.get("location"):
        lines[-1] += f" · 📍 {p['location']}"
    if links:
        lines += ["", links]
    if p.get("about"):
        lines += ["", p["about"].strip()]
    return "\n".join(lines)


def build_now(p):
    """What you're doing right now, derived purely from dates."""
    lines = []
    for e in p.get("experience", []):
        s = status(e)
        where = f"{e['org']}" + (f" ({e['team']})" if e.get("team") else "")
        if s == "current":
            lines.append(f"- 💼 **{e['role']}** at {where}")
        elif s == "upcoming":
            lines.append(f"- 🔜 Incoming **{e['role']}** at {where}, starting {fmt_month(to_date(e['start']))}")
    for ed in p.get("education", []):
        s = status(ed)
        loc = f" in {ed['location']}" if ed.get("location") else ""
        if s == "current":
            lines.append(f"- 🎓 Studying at **{ed['school']}**{loc}")
        elif s == "upcoming":
            lines.append(f"- ✈️ Heading to **{ed['school']}**{loc} in {fmt_month(to_date(ed['start']))}")
    if not lines:
        return ""
    return "## 📌 Right now\n\n" + "\n".join(lines)


def build_news(p):
    items = sorted(p.get("news", []), key=lambda n: to_date(n["date"]), reverse=True)[:6]
    if not items:
        return ""
    out = ["## 📰 Latest updates", ""]
    for n in items:
        d = to_date(n["date"])
        badge = " 🆕" if (TODAY - d).days <= NEW_BADGE_DAYS else ""
        out.append(f"- **{d.strftime('%b %Y')}**: {n['text']}{badge}")
    return "\n".join(out)


def build_experience(p):
    rows = []
    for e in sorted(p.get("experience", []), key=lambda e: to_date(e["start"]), reverse=True):
        label = {"upcoming": "Incoming", "current": "Current", "past": ""}[status(e)]
        role = f"{e['role']}" + (f" · {e['team']}" if e.get("team") else "")
        dates = f"{fmt_month(to_date(e['start']))} – {fmt_month(to_date(e.get('end')))}"
        rows.append(f"| {role} | {e['org']} | {e.get('location','')} | {dates} | {label} |")
    edu = []
    for ed in sorted(p.get("education", []), key=lambda e: to_date(e["start"]), reverse=True):
        dates = f"{fmt_month(to_date(ed['start']))} – {fmt_month(to_date(ed.get('end')))}"
        edu.append(f"- **{ed['school']}**, {ed.get('detail','')} ({dates})")
    out = []
    if rows:
        out += ["## 💼 Experience", "", "| Role | Firm | Location | Dates | |",
                "|---|---|---|---|---|", *rows, ""]
    if edu:
        out += ["## 🎓 Education", "", *edu, ""]
    if p.get("skills"):
        out += ["## 🧰 Skills", "", " · ".join(f"`{s}`" for s in p["skills"])]
    return "\n".join(out)


def build_activity(user, repos, events):
    out = ["## 🛠️ What I've been building", ""]
    if not repos:
        out.append("_Nothing public yet. Check back soon._")
    for r in repos[:5]:
        pushed = datetime.strptime(r["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        desc = f": {r['description']}" if r.get("description") else ""
        lang = f" · `{r['language']}`" if r.get("language") else ""
        out.append(f"- [**{r['name']}**]({r['html_url']}){desc}{lang} · updated {pushed:%b %d}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    pushes = [e for e in events if e["type"] == "PushEvent"
              and datetime.strptime(e["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) > cutoff]
    commits = sum(e["payload"].get("size", len(e["payload"].get("commits", []))) for e in pushes)
    active = len({e["repo"]["name"] for e in pushes})
    if commits:
        out += ["", f"**Last 30 days:** {commits} commits across {active} repo{'s' * (active != 1)}"]
    return "\n".join(out)


# ── main ─────────────────────────────────────────────────────
def main():
    p = yaml.safe_load(PROFILE.read_text())
    user = os.environ.get("GH_USERNAME") or p["github_username"]
    text = README.read_text()

    text = replace_section(text, "header", build_header(p))
    text = replace_section(text, "now", build_now(p))
    text = replace_section(text, "news", build_news(p))
    text = replace_section(text, "experience", build_experience(p))

    if "--offline" not in sys.argv:
        try:
            repos, events = github_activity(user)
            text = replace_section(text, "activity", build_activity(user, repos, events))
        except Exception as e:  # keep the old activity block rather than fail
            print(f"warning: GitHub API failed ({e}); keeping previous activity section")

    stamp = datetime.now(timezone.utc).strftime("%b %d, %Y")
    text = replace_section(text, "updated", f"<sub>🤖 Auto-updated {stamp}</sub>")
    README.write_text(text)
    print("README.md updated")


if __name__ == "__main__":
    main()

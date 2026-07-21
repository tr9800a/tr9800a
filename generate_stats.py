#!/usr/bin/env python3
"""Render neofetch-style stats SVGs from the vendored github_stats engine.

Customization layer over jstrieb/github-stats (GPL-3.0). Keeps github_stats.py
pristine; adds a followers lookup + avatar embed + native-SVG language bar.
"""
import asyncio
import base64
import os

import aiohttp

from github_stats import Stats

# Fallback colors for languages GitHub linguist doesn't give us a color for.
FALLBACK_COLOR = "#8b949e"
BAR_WIDTH = 440          # px, width of the language bar
TOP_LANGS = 6            # languages shown in bar + legend


async def fetch_followers(session: aiohttp.ClientSession, user: str, token: str) -> int:
    headers = {"Authorization": f"token {token}"}
    async with session.get(f"https://api.github.com/users/{user}", headers=headers) as r:
        r.raise_for_status()
        data = await r.json()
        return int(data.get("followers", 0))


async def fetch_avatar_data_uri(session: aiohttp.ClientSession, user: str, token: str) -> str:
    headers = {"Authorization": f"token {token}"}
    async with session.get(f"https://api.github.com/users/{user}", headers=headers) as r:
        r.raise_for_status()
        meta = await r.json()
    url = meta["avatar_url"]
    async with session.get(url) as r:
        r.raise_for_status()
        raw = await r.read()
        ctype = r.headers.get("Content-Type", "image/png").split(";")[0]
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{ctype};base64,{b64}"


def build_language_svg(languages: dict) -> tuple[str, str]:
    """Return (lang_bar_svg, lang_legend_svg) as native SVG element strings."""
    items = sorted(languages.items(), key=lambda kv: kv[1].get("prop", 0), reverse=True)
    items = items[:TOP_LANGS]
    total = sum(v.get("prop", 0) for _, v in items) or 1.0

    # Bar: rounded container with colored segments.
    bar = [f'<rect x="0" y="0" width="{BAR_WIDTH}" height="8" rx="4" fill="#30363d"/>']
    x = 0.0
    for _, data in items:
        w = BAR_WIDTH * (data.get("prop", 0) / total)
        color = data.get("color") or FALLBACK_COLOR
        bar.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="8" fill="{color}"/>')
        x += w

    # Legend: colored dot + "Name pct%", laid out in up to 3 columns.
    legend = []
    col_w = BAR_WIDTH / 3
    for i, (lang, data) in enumerate(items):
        col = i % 3
        row = i // 3
        gx = col * col_w
        gy = row * 18
        color = data.get("color") or FALLBACK_COLOR
        pct = data.get("prop", 0)
        legend.append(
            f'<circle cx="{gx + 4:.1f}" cy="{gy + 4:.1f}" r="4" fill="{color}"/>'
            f'<text x="{gx + 14:.1f}" y="{gy + 8:.1f}" font-size="11" fill="#8b949e">'
            f'{lang} {pct:.1f}%</text>'
        )
    return "".join(bar), "".join(legend)


def fill(template: str, values: dict) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{ " + key + " }}", str(val))
    return out


async def main() -> None:
    token = os.environ["ACCESS_TOKEN"]
    user = os.environ.get("GITHUB_ACTOR") or os.environ["USER_NAME"]

    async with aiohttp.ClientSession() as session:
        s = Stats(user, token, session)
        name = await s.name
        repos = len(await s.repos)
        commits = await s.total_contributions
        stars = await s.stargazers
        added, deleted = await s.lines_changed
        followers = await fetch_followers(session, user, token)
        avatar = await fetch_avatar_data_uri(session, user, token)
        lang_bar, lang_legend = build_language_svg(await s.languages)

    values = {
        "avatar": avatar,
        "repos": f"{repos:,}",
        "commits": f"{commits:,}",
        "stars": f"{stars:,}",
        "followers": f"{followers:,}",
        "loc_add": f"{added:,}",
        "loc_del": f"{deleted:,}",
        "lang_bar": lang_bar,
        "lang_legend": lang_legend,
    }

    for mode in ("dark", "light"):
        with open(f"templates/{mode}_mode.svg", "r", encoding="utf-8") as f:
            template = f.read()
        rendered = fill(template, values)
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"wrote {mode}_mode.svg")


if __name__ == "__main__":
    asyncio.run(main())

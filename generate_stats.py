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


async def fetch_user_meta(session: aiohttp.ClientSession, user: str, token: str) -> dict:
    headers = {"Authorization": f"token {token}"}
    async with session.get(f"https://api.github.com/users/{user}", headers=headers) as r:
        r.raise_for_status()
        return await r.json()


async def avatar_data_uri(session: aiohttp.ClientSession, avatar_url: str) -> str:
    async with session.get(avatar_url) as r:
        r.raise_for_status()
        raw = await r.read()
        ctype = r.headers.get("Content-Type", "image/png").split(";")[0]
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{ctype};base64,{b64}"


def build_language_svg(languages: dict) -> tuple[str, str]:
    """Return (lang_bar_svg, lang_legend_svg) as native SVG element strings."""
    items = sorted(languages.items(), key=lambda kv: kv[1].get("prop", 0), reverse=True)
    items = items[:TOP_LANGS]

    # Bar: rounded container with colored segments sized by true proportion
    # (share of the user's entire language footprint). Any remainder stays the
    # background color, representing languages outside the shown few.
    bar = [f'<rect x="0" y="0" width="{BAR_WIDTH}" height="8" rx="4" fill="#30363d"/>']
    x = 0.0
    for _, data in items:
        w = BAR_WIDTH * (data.get("prop", 0) / 100.0)
        color = data.get("color") or FALLBACK_COLOR
        bar.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="8" fill="{color}"/>')
        x += w

    # Legend: colored dot + "Name pct%", flowing left-to-right and wrapping to
    # a new row when the next item would overrun the bar width. Item widths are
    # estimated from the monospace advance so long language names don't collide.
    legend = []
    char_w = 6.6      # approx advance per char at font-size 11 (monospace)
    dot_w = 14        # dot + gap before the label
    gap = 20          # gap between items
    x = 0.0
    row = 0
    for lang, data in items:
        color = data.get("color") or FALLBACK_COLOR
        pct = data.get("prop", 0)
        label = f"{lang} {pct:.1f}%"
        item_w = dot_w + len(label) * char_w
        if x > 0 and x + item_w > BAR_WIDTH:
            x = 0.0
            row += 1
        gy = row * 18
        legend.append(
            f'<circle cx="{x + 4:.1f}" cy="{gy + 4:.1f}" r="4" fill="{color}"/>'
            f'<text x="{x + dot_w:.1f}" y="{gy + 8:.1f}" font-size="11" fill="#8b949e">'
            f'{label}</text>'
        )
        x += item_w + gap
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
        repos = len(await s.repos)
        commits = await s.total_contributions
        stars = await s.stargazers
        added, deleted = await s.lines_changed
        meta = await fetch_user_meta(session, user, token)
        followers = int(meta.get("followers", 0))
        avatar = await avatar_data_uri(session, meta["avatar_url"])
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

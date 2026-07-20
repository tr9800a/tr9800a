# Auto-updating neofetch-style Profile README — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tr9800a/tr9800a` — a GitHub profile README that displays a neofetch/terminal-style, theme-aware, self-updating stats card (repos, commits, stars, followers, lines of code ±, top languages), regenerated daily by GitHub Actions.

**Architecture:** Vendor the GPL-3.0 Python stats engine `github_stats.py` from `jstrieb/github-stats` at its last Python commit `0de78de1e603`. A thin renderer `generate_stats.py` pulls values from the engine's async `Stats` class, adds a followers lookup + embedded avatar, fills two native-SVG templates (dark/light), and writes `dark_mode.svg` + `light_mode.svg`. A workflow runs the renderer on a daily cron and commits the regenerated SVGs. `README.md` uses a `<picture>` block that swaps SVGs by the viewer's GitHub theme.

**Tech Stack:** Python 3.11+, `aiohttp`, `requests`; GitHub GraphQL + REST API; GitHub Actions; native SVG (`<text>`/`<rect>`/`<image>` — NO `<foreignObject>`, for maximum GitHub render reliability).

## Global Constraints

- Repo path: `/Users/tristan.mckinnon/Documents/GitHub/tr9800a`, pushed to `github.com/tr9800a/tr9800a` (public).
- Stats engine is **vendored verbatim** from `jstrieb/github-stats@0de78de1e603` and kept pristine — do NOT edit `github_stats.py`; all customization lives in `generate_stats.py` and the templates.
- License: **GPL-3.0** (derivative of GPL-3.0 upstream). `LICENSE` present; attribution to jstrieb in `README.md`.
- The `Stats` constructor is `Stats(username, access_token, session, exclude_repos=None, exclude_langs=None, ignore_forked_repos=False)`.
- Async properties available: `name` (str), `stargazers` (int), `forks` (int), `languages` (dict `lang -> {size,color,prop,...}`), `repos` (Set[str]; count = `len`), `total_contributions` (int), `lines_changed` (Tuple[int,int] = additions, deletions), `views` (int).
- **Followers is NOT on `Stats`** — fetch via `GET https://api.github.com/users/{user}` → `.followers`.
- Private repos are **included** (the classic PAT has `repo` scope; jstrieb includes private by default). Do not set any exclude-private flag.
- Card rows: `Repos`, `Commits` (= `total_contributions`), `Stars`, `Followers`, `Lines of code: +add / -del`, plus a top-languages color bar + legend. **No uptime/age row. No views row. No "contributed-to" sub-count** (upstream can't cleanly separate it).
- Username env var read by the renderer: `GITHUB_ACTOR` (set to `tr9800a`).
- Token is provided out-of-band as `ACCESS_TOKEN`; never commit it or write it to a file.
- Git author for commits: `-c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com"`.

---

## File structure

- `github_stats.py` — vendored engine (pristine).
- `generate_stats.py` — our renderer (all customization).
- `templates/dark_mode.svg`, `templates/light_mode.svg` — native-SVG neofetch cards.
- `dark_mode.svg`, `light_mode.svg` — generated output at repo root (committed).
- `.github/workflows/build.yaml` — daily cron + push + manual dispatch.
- `README.md` — `<picture>` block + jstrieb attribution.
- `requirements.txt`, `LICENSE`, `.gitignore`.

---

### Task 1: Repo skeleton (license, deps, README, ignore)

**Files:**
- Create: `LICENSE`, `requirements.txt`, `.gitignore`, `README.md`

**Interfaces:**
- Produces: repo root files; `README.md` references `dark_mode.svg`/`light_mode.svg` (created in Task 4).

- [ ] **Step 1: Add GPL-3.0 LICENSE**

```bash
cd /Users/tristan.mckinnon/Documents/GitHub/tr9800a
curl -fsSL https://www.gnu.org/licenses/gpl-3.0.txt -o LICENSE
head -1 LICENSE   # expect: "                    GNU GENERAL PUBLIC LICENSE"
```

- [ ] **Step 2: Write `requirements.txt`**

```
aiohttp
requests
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.env
```

- [ ] **Step 4: Write `README.md`**

```markdown
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="./dark_mode.svg">
  <source media="(prefers-color-scheme: light)" srcset="./light_mode.svg">
  <img alt="Tristan McKinnon's GitHub stats" src="./light_mode.svg">
</picture>

</div>

<!--
Stats card auto-generated daily by .github/workflows/build.yaml.
Stats engine vendored from jstrieb/github-stats (GPL-3.0):
https://github.com/jstrieb/github-stats — see LICENSE.
-->
```

- [ ] **Step 5: Verify files exist**

Run: `ls LICENSE requirements.txt .gitignore README.md`
Expected: all four listed, no error.

- [ ] **Step 6: Commit**

```bash
git add LICENSE requirements.txt .gitignore README.md
git -c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com" \
  commit -m "Add repo skeleton: GPL-3.0 license, deps, README picture block"
```

---

### Task 2: Vendor the stats engine and verify a live query

**Files:**
- Create: `github_stats.py` (fetched verbatim from upstream at pinned SHA)

**Interfaces:**
- Produces: `github_stats.Stats` class with the async properties listed in Global Constraints; importable and runnable against the live API.

- [ ] **Step 1: Vendor `github_stats.py` at the pinned commit**

```bash
cd /Users/tristan.mckinnon/Documents/GitHub/tr9800a
gh api "repos/jstrieb/github-stats/contents/github_stats.py?ref=0de78de1e603" \
  --jq '.content' | base64 -d > github_stats.py
python3 -c "import ast; ast.parse(open('github_stats.py').read()); print('parses OK')"
```
Expected: `parses OK`

- [ ] **Step 2: Create a venv and install deps**

```bash
python3 -m venv .venv && ./.venv/bin/pip -q install -r requirements.txt
```
Expected: installs `aiohttp`, `requests` without error.

- [ ] **Step 3: Live smoke test (this is the test)**

Run (replace `<TOKEN>` with the provided ACCESS_TOKEN — do not paste into a file):
```bash
ACCESS_TOKEN='<TOKEN>' GITHUB_ACTOR='tr9800a' ./.venv/bin/python github_stats.py
```
Expected: prints a human-readable stats block (name, stars, forks, contributions, lines changed, repos, languages) with **non-zero, real numbers** for account `tr9800a`. If it errors on auth, the token scope is wrong — stop and report.

- [ ] **Step 4: Commit**

```bash
git add github_stats.py
git -c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com" \
  commit -m "Vendor jstrieb/github-stats engine (GPL-3.0) at 0de78de1e603"
```

---

### Task 3: Neofetch SVG templates (dark + light)

**Files:**
- Create: `templates/dark_mode.svg`, `templates/light_mode.svg`

**Interfaces:**
- Produces: two SVG templates containing these exact placeholders, filled by Task 4:
  `{{ avatar }}`, `{{ repos }}`, `{{ commits }}`, `{{ stars }}`, `{{ followers }}`,
  `{{ loc_add }}`, `{{ loc_del }}`, `{{ lang_bar }}`, `{{ lang_legend }}`.

- [ ] **Step 1: Write `templates/dark_mode.svg`**

```svg
<svg width="500" height="270" viewBox="0 0 500 270" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" aria-labelledby="t d">
  <title id="t">Tristan McKinnon's GitHub stats</title>
  <desc id="d">Repos {{ repos }}, Commits {{ commits }}, Stars {{ stars }}, Followers {{ followers }}, Lines of code +{{ loc_add }} / -{{ loc_del }}</desc>
  <style>
    text{font-family:'SF Mono','Consolas','Menlo','DejaVu Sans Mono',monospace;}
    .win{fill:#161b22;stroke:#30363d;}
    .prompt{fill:#8b949e;font-size:12px;}
    .name{fill:#e6edf3;font-size:15px;font-weight:bold;}
    .rule{fill:#30363d;font-size:13px;}
    .key{fill:#58a6ff;font-size:13px;}
    .sep{fill:#8b949e;font-size:13px;}
    .val{fill:#c9d1d9;font-size:13px;}
    .add{fill:#3fb950;font-size:13px;}
    .del{fill:#f85149;font-size:13px;}
    .dim{fill:#8b949e;font-size:11px;}
    .cur{fill:#58a6ff;font-size:12px;}
  </style>
  <rect class="win" x="1" y="1" width="498" height="268" rx="8"/>
  <circle cx="20" cy="20" r="5" fill="#ff5f56"/>
  <circle cx="38" cy="20" r="5" fill="#ffbd2e"/>
  <circle cx="56" cy="20" r="5" fill="#27c93f"/>
  <text class="prompt" x="250" y="24" text-anchor="middle">tr9800a@github:~$ neofetch</text>
  <clipPath id="av"><rect x="30" y="56" width="120" height="120" rx="10"/></clipPath>
  <image x="30" y="56" width="120" height="120" clip-path="url(#av)" xlink:href="{{ avatar }}" preserveAspectRatio="xMidYMid slice"/>
  <text class="dim" x="90" y="196" text-anchor="middle">@tr9800a</text>
  <text class="name" x="185" y="66">Tristan McKinnon</text>
  <text class="rule" x="185" y="82">────────────────────────</text>
  <text x="185" y="106"><tspan class="key">Repos</tspan><tspan class="sep">        : </tspan><tspan class="val">{{ repos }}</tspan></text>
  <text x="185" y="128"><tspan class="key">Commits</tspan><tspan class="sep">      : </tspan><tspan class="val">{{ commits }}</tspan></text>
  <text x="185" y="150"><tspan class="key">Stars</tspan><tspan class="sep">        : </tspan><tspan class="val">{{ stars }}</tspan></text>
  <text x="185" y="172"><tspan class="key">Followers</tspan><tspan class="sep">    : </tspan><tspan class="val">{{ followers }}</tspan></text>
  <text x="185" y="194"><tspan class="key">Lines of code</tspan><tspan class="sep">: </tspan><tspan class="add">+{{ loc_add }}</tspan><tspan class="sep"> / </tspan><tspan class="del">-{{ loc_del }}</tspan></text>
  <text class="key" x="30" y="224" font-size="12">Languages</text>
  <g transform="translate(30,230)">{{ lang_bar }}</g>
  <g transform="translate(30,252)">{{ lang_legend }}</g>
</svg>
```

- [ ] **Step 2: Write `templates/light_mode.svg`** (identical geometry, light palette)

```svg
<svg width="500" height="270" viewBox="0 0 500 270" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" aria-labelledby="t d">
  <title id="t">Tristan McKinnon's GitHub stats</title>
  <desc id="d">Repos {{ repos }}, Commits {{ commits }}, Stars {{ stars }}, Followers {{ followers }}, Lines of code +{{ loc_add }} / -{{ loc_del }}</desc>
  <style>
    text{font-family:'SF Mono','Consolas','Menlo','DejaVu Sans Mono',monospace;}
    .win{fill:#ffffff;stroke:#d0d7de;}
    .prompt{fill:#57606a;font-size:12px;}
    .name{fill:#1f2328;font-size:15px;font-weight:bold;}
    .rule{fill:#d0d7de;font-size:13px;}
    .key{fill:#0969da;font-size:13px;}
    .sep{fill:#57606a;font-size:13px;}
    .val{fill:#1f2328;font-size:13px;}
    .add{fill:#1a7f37;font-size:13px;}
    .del{fill:#cf222e;font-size:13px;}
    .dim{fill:#57606a;font-size:11px;}
    .cur{fill:#0969da;font-size:12px;}
  </style>
  <rect class="win" x="1" y="1" width="498" height="268" rx="8"/>
  <circle cx="20" cy="20" r="5" fill="#ff5f56"/>
  <circle cx="38" cy="20" r="5" fill="#ffbd2e"/>
  <circle cx="56" cy="20" r="5" fill="#27c93f"/>
  <text class="prompt" x="250" y="24" text-anchor="middle">tr9800a@github:~$ neofetch</text>
  <clipPath id="av"><rect x="30" y="56" width="120" height="120" rx="10"/></clipPath>
  <image x="30" y="56" width="120" height="120" clip-path="url(#av)" xlink:href="{{ avatar }}" preserveAspectRatio="xMidYMid slice"/>
  <text class="dim" x="90" y="196" text-anchor="middle">@tr9800a</text>
  <text class="name" x="185" y="66">Tristan McKinnon</text>
  <text class="rule" x="185" y="82">────────────────────────</text>
  <text x="185" y="106"><tspan class="key">Repos</tspan><tspan class="sep">        : </tspan><tspan class="val">{{ repos }}</tspan></text>
  <text x="185" y="128"><tspan class="key">Commits</tspan><tspan class="sep">      : </tspan><tspan class="val">{{ commits }}</tspan></text>
  <text x="185" y="150"><tspan class="key">Stars</tspan><tspan class="sep">        : </tspan><tspan class="val">{{ stars }}</tspan></text>
  <text x="185" y="172"><tspan class="key">Followers</tspan><tspan class="sep">    : </tspan><tspan class="val">{{ followers }}</tspan></text>
  <text x="185" y="194"><tspan class="key">Lines of code</tspan><tspan class="sep">: </tspan><tspan class="add">+{{ loc_add }}</tspan><tspan class="sep"> / </tspan><tspan class="del">-{{ loc_del }}</tspan></text>
  <text class="key" x="30" y="224" font-size="12">Languages</text>
  <g transform="translate(30,230)">{{ lang_bar }}</g>
  <g transform="translate(30,252)">{{ lang_legend }}</g>
</svg>
```

- [ ] **Step 3: Verify both templates are well-formed XML**

Run:
```bash
python3 -c "import xml.dom.minidom as m; [m.parse(f) for f in ('templates/dark_mode.svg','templates/light_mode.svg')]; print('both well-formed')"
```
Expected: `both well-formed`

- [ ] **Step 4: Commit**

```bash
git add templates/dark_mode.svg templates/light_mode.svg
git -c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com" \
  commit -m "Add neofetch-style dark/light SVG templates"
```

---

### Task 4: Renderer `generate_stats.py` → produces the SVGs

**Files:**
- Create: `generate_stats.py`

**Interfaces:**
- Consumes: `github_stats.Stats`; env `ACCESS_TOKEN`, `GITHUB_ACTOR`; templates from Task 3.
- Produces: `dark_mode.svg`, `light_mode.svg` at repo root with all placeholders replaced.

- [ ] **Step 1: Write `generate_stats.py`**

```python
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
```

- [ ] **Step 2: Run the renderer against the live API (this is the test)**

```bash
cd /Users/tristan.mckinnon/Documents/GitHub/tr9800a
ACCESS_TOKEN='<TOKEN>' GITHUB_ACTOR='tr9800a' ./.venv/bin/python generate_stats.py
```
Expected: prints `wrote dark_mode.svg` and `wrote light_mode.svg`.

- [ ] **Step 3: Verify output is filled and well-formed**

```bash
grep -c '{{' dark_mode.svg light_mode.svg   # expect 0 in each (no leftover placeholders)
python3 -c "import xml.dom.minidom as m; [m.parse(f) for f in ('dark_mode.svg','light_mode.svg')]; print('valid')"
open dark_mode.svg light_mode.svg           # eyeball: avatar renders, numbers real, bar shows colors
```
Expected: `0` and `0`, then `valid`, then both cards look right in the browser.

- [ ] **Step 4: Commit**

```bash
git add generate_stats.py dark_mode.svg light_mode.svg
git -c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com" \
  commit -m "Add renderer and initial generated stats SVGs"
```

---

### Task 5: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/build.yaml`

**Interfaces:**
- Consumes: repo secret `ACCESS_TOKEN`, repo variable `USER_NAME` (set in Task 6); `generate_stats.py`.
- Produces: committed, regenerated `*.svg` on schedule/push/dispatch.

- [ ] **Step 1: Write `.github/workflows/build.yaml`**

```yaml
name: Generate profile stats

on:
  push:
    branches: [main]
  schedule:
    - cron: "30 5 * * *"   # daily 05:30 UTC
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: generate-stats
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate stats SVGs
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
          GITHUB_ACTOR: ${{ vars.USER_NAME }}
        run: python generate_stats.py

      - name: Commit updated SVGs
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add dark_mode.svg light_mode.svg
          git diff --staged --quiet || git commit -m "chore: refresh profile stats"
          git push
```

- [ ] **Step 2: Verify workflow YAML parses**

```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/build.yaml')); print('yaml ok')"
```
Expected: `yaml ok` (install pyyaml into the venv first if needed: `./.venv/bin/pip -q install pyyaml` and use `./.venv/bin/python`).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yaml
git -c user.name="tr9800a" -c user.email="tristan.mckinnon@axleinfo.com" \
  commit -m "Add daily stats-refresh workflow"
```

---

### Task 6: Publish repo, wire secrets, verify end-to-end

**Files:** none (infra).

**Interfaces:**
- Consumes: everything above + the provided token.
- Produces: live `github.com/tr9800a/tr9800a` rendering the card on the profile.

- [ ] **Step 1: Create the repo and push**

```bash
cd /Users/tristan.mckinnon/Documents/GitHub/tr9800a
git branch -M main
gh repo create tr9800a/tr9800a --public --source=. --remote=origin --push
```
Expected: repo created, `main` pushed.

- [ ] **Step 2: Set the secret and username variable**

```bash
printf '%s' '<TOKEN>' | gh secret set ACCESS_TOKEN --repo tr9800a/tr9800a
gh variable set USER_NAME --repo tr9800a/tr9800a --body 'tr9800a'
gh secret list --repo tr9800a/tr9800a
gh variable list --repo tr9800a/tr9800a
```
Expected: `ACCESS_TOKEN` listed as a secret; `USER_NAME=tr9800a` listed as a variable.

- [ ] **Step 3: Trigger the workflow and confirm it passes**

```bash
gh workflow run build.yaml --repo tr9800a/tr9800a
sleep 15
gh run list --repo tr9800a/tr9800a --workflow build.yaml --limit 1
# poll until status=completed, conclusion=success:
gh run watch --repo tr9800a/tr9800a "$(gh run list --repo tr9800a/tr9800a --workflow build.yaml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```
Expected: run concludes `success` and commits refreshed SVGs (or "nothing to commit" if unchanged).

- [ ] **Step 4: Confirm the profile renders**

```bash
gh api repos/tr9800a/tr9800a/contents/dark_mode.svg --jq '.size'   # >0
echo "Open https://github.com/tr9800a in both light and dark theme to eyeball the card."
```
Expected: SVG present in repo; card visible on the profile page in both themes.

- [ ] **Step 5: Remind about token rotation**

The token was shared in chat. Instruct the user to regenerate it at
`github.com/settings/tokens`, then update the repo secret:
```bash
printf '%s' '<NEW_TOKEN>' | gh secret set ACCESS_TOKEN --repo tr9800a/tr9800a
```

---

## Self-review

- **Spec coverage:** engine (T2), templates/theme-aware (T3), renderer with followers + LOC ± + avatar embed (T4), workflow daily refresh (T5), publish + secret + verify (T6), README picture block + GPL license + attribution (T1). Uptime dropped, private included, views/contributed-to excluded — all matched. ✓
- **Placeholder scan:** `<TOKEN>` is an intentional runtime secret substitution, not a plan gap; all code blocks are complete. ✓
- **Type consistency:** placeholder names in T3 templates (`avatar, repos, commits, stars, followers, loc_add, loc_del, lang_bar, lang_legend`) exactly match the `values` dict keys in T4. `Stats` property names match Global Constraints. ✓

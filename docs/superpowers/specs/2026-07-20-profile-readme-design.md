# Design: Auto-updating neofetch-style GitHub profile README

**Repo:** `tr9800a/tr9800a` (GitHub profile README — the special repo whose name matches the username)
**Date:** 2026-07-20
**Status:** Approved design, pending spec review

## Goal

A neofetch / terminal-style, theme-aware, self-updating profile card in the spirit of
[Andrew6rant/Andrew6rant](https://github.com/Andrew6rant/Andrew6rant), built on the
GPL-3.0 `jstrieb/github-stats` engine with our own SVG templates. The card looks like a
Linux terminal dump: a prompt-style header, monospace `key: value` stat rows, an embedded
avatar on the left, and a top-languages color bar. Numbers refresh automatically via
GitHub Actions.

## Confirmed decisions

- **Base engine:** `jstrieb/github-stats` (GPL-3.0), pinned to the **last Python-era commit
  `0de78de1e603` (2022-02-17)** — upstream HEAD has since been rewritten in Zig and exposes
  fewer fields (no followers, no added/removed LOC split), so we vendor the Python engine at that
  commit. Our own SVG templates, look "inspired by" Andrew6rant (not byte-identical). GPL-3.0
  LICENSE + attribution to jstrieb included.
- **Followers** is not exposed by the vendored `Stats` class; our generator fetches it with a
  small REST call to `GET /users/{username}` using the same token. The vendored `github_stats.py`
  stays pristine (easier provenance/updates).
- **Repo views** row is dropped (requires per-repo push/traffic access; brittle) — already out of scope.
- **Commits row** uses `total_contributions` (GitHub contribution-calendar semantics), labelled "Commits".
- **Display name / header:** terminal-prompt style — `tr9800a@github:~$` with the full name
  `Tristan McKinnon` shown as the card title.
- **Uptime/age row:** dropped entirely (no birthdate exposed).
- **Repo scope:** include **private** repos in totals (lines of code, commits). Private repo
  *names* are never shown — only aggregate numbers. Requires a PAT with all-repositories read access.
- **Left-side graphic:** the GitHub avatar (`https://avatars.githubusercontent.com/u/79180812?v=4`),
  embedded as a **base64 data URI** inside each SVG (external image refs are stripped by GitHub's
  README sanitizer, so a URL would not render).
- **Build location:** sibling folder `../tr9800a` (this repo), pushed to `github.com/tr9800a/tr9800a`.

## Architecture / data flow

```
GitHub Actions (schedule: daily cron  +  push  +  workflow_dispatch)
        │  env: ACCESS_TOKEN (fine-grained PAT), USER_NAME=tr9800a
        ▼
  generate_stats.py ──► GitHub GraphQL + REST API
        │                 repos, contributed-to count, commits, stars,
        │                 followers, LOC added/removed (incl. private),
        │                 most-used languages
        ├──► cache/*.txt          per-repo LOC cache (hash-keyed) to avoid recompute
        └──► render templates ──► dark_mode.svg + light_mode.svg  (committed back to repo)
                                        │
README.md  <picture>  ── GitHub swaps SVG by viewer's light/dark theme
```

## Components (files in `tr9800a/tr9800a`)

- `generate_stats.py` — stats engine adapted from `jstrieb/github-stats` (GPL-3.0). Async
  GraphQL client; counts repos/commits/stars/followers; computes LOC added/removed by walking
  repo commit history; caches per-repo LOC keyed by a content hash so unchanged repos are not
  re-queried. Reads `ACCESS_TOKEN` and `USER_NAME` from env. The birthday/uptime logic from the
  Andrew6rant variant is **removed**.
- `templates/dark_mode.svg`, `templates/light_mode.svg` — **our own** neofetch terminal card.
  - Terminal window chrome (title bar with prompt `tr9800a@github:~$`).
  - Left: embedded avatar (base64 data URI).
  - Right: monospace stat rows (see "Card content").
  - Bottom: most-used-languages horizontal color bar with percentages.
  - Placeholders substituted at build time: `{{ name }}`, `{{ repos }}`, `{{ contrib }}`,
    `{{ commits }}`, `{{ stars }}`, `{{ followers }}`, `{{ loc_add }}`, `{{ loc_del }}`,
    `{{ loc_total }}`, and language bar segments.
  - Two files differ only in palette (dark vs. light background/foreground).
- `.github/workflows/build.yaml` — triggers: `schedule` (daily cron), `push` to default branch,
  and `workflow_dispatch`. Steps: checkout, set up Python, `pip install -r requirements.txt`,
  run `generate_stats.py`, commit changed `*.svg` + `cache/` back to the repo (skip commit if
  no diff). Uses repo secret `ACCESS_TOKEN` and repo variable `USER_NAME`.
- `README.md` — the theme-aware `<picture>` block only:
  ```html
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset=".../dark_mode.svg">
    <source media="(prefers-color-scheme: light)" srcset=".../light_mode.svg">
    <img alt="Tristan McKinnon's GitHub stats" src=".../light_mode.svg">
  </picture>
  ```
- `LICENSE` — GPL-3.0.
- `requirements.txt` — `requests` (or `aiohttp`), `lxml`, `python-dateutil` as needed by the engine.
- `README` attribution line crediting `jstrieb/github-stats`.
- `.gitignore` — Python caches, venv.

## Card content

- **Header/title:** `tr9800a@github:~$` prompt, card title `Tristan McKinnon`.
- **Rows:**
  - `Repos: N {contributed to: M}`
  - `Commits: N`
  - `Stars: N`
  - `Followers: N`
  - `Lines of code: +{added} / -{removed}` (private included; aggregate only)
- **Most-used languages:** color bar + top languages with percentages.
- **No uptime/age row.**
- Monospace, dark-first; theme-aware light variant.

## Responsibilities

**Automated (Claude via `gh`):**
1. Write all files into `../tr9800a`.
2. Run `generate_stats.py` locally with a token to verify SVG rendering with real numbers.
3. `gh repo create tr9800a/tr9800a --public --source=. --push`.
4. Set repo variable `USER_NAME=tr9800a` (`gh variable set`).
5. Trigger the workflow once via `workflow_dispatch` and confirm the committed SVGs render.

**Manual (user — one step):**
- Create a **fine-grained Personal Access Token**, All repositories, read-only permissions:
  Metadata, Contents, Commit statuses, plus account Followers / Starring. Then either paste it so
  Claude runs `gh secret set ACCESS_TOKEN`, or add it in the repo Settings → Secrets UI.
  (A classic PAT with `repo` + `read:user` scope also works.)

## Verification

- Local dry run: `USER_NAME=tr9800a ACCESS_TOKEN=... python generate_stats.py` produces
  `dark_mode.svg` and `light_mode.svg` with non-placeholder numbers; open both to confirm layout
  and that the avatar renders.
- Post-push: run the workflow via `workflow_dispatch`; confirm it commits updated SVGs and that
  the profile page (`github.com/tr9800a`) renders the card in both light and dark themes.

## Out of scope

- Repo traffic/views stats (requires per-repo push access; brittle).
- Any changes to the existing `tr9800a.github.io` site.
- Typing/animation beyond a simple static blinking-cursor glyph (kept minimal for reliability).

## Licensing note

`jstrieb/github-stats` is GPL-3.0; derivative work is therefore GPL-3.0 and the LICENSE is
included with attribution. Andrew6rant's repo (no license) is used only as visual inspiration,
not copied.

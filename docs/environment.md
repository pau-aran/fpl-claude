# Environments — setup and network reality

Two environments run this project. **The local Windows workstation reaches every
data domain; the cloud sandbox does not.** Sections below, newest first.

## Local Windows workstation (tested 2026-07-25)

The owner's machine — and the one difference that matters: **egress is OPEN.**
Tested live, all `200`:

| Domain | Status |
|---|---|
| `fantasy.premierleague.com/api/bootstrap-static/` | **200 — reachable** |
| `www.football-data.co.uk` (Dixon-Coles training CSVs) | **200 — reachable** |
| `understat.com` | **200 — reachable** |

So the "first live 2026/27 data run" (NEXT-STEPS §1) and the Dixon-Coles fetch
are **not blocked here** — they were only ever blocked in the cloud sandbox.
That item can be run from this machine whenever the owner wants it.

Setup (there is no `session-start.sh` equivalent on Windows — the hook is bash):

```powershell
# Python: system PATH only has the Microsoft Store stub; miniconda3 is the real one.
# uv is installed at C:\Users\pau_8\.local\bin\uv.exe
& 'C:\Users\pau_8\.local\bin\uv.exe' venv --python 3.13 .venv
$env:UV_LINK_MODE='copy'
& 'C:\Users\pau_8\.local\bin\uv.exe' pip install -e '.[dev,optimize,models]'

& .\.venv\Scripts\python.exe -m pytest -q                    # 67 passed, 1 skipped
& .\.venv\Scripts\python.exe -m ruff check src tests notebooks --output-format concise
```

`uv venv` writes a self-ignoring `.venv/.gitignore`, so the venv never shows up
in `git status`. Worktrees need their own venv (an editable install resolves to
the *installing* checkout's `src/`, so a shared venv would silently test the
wrong tree).

**Lint baseline:** local ruff is **0.16.0**, newer than the sandbox's, and its
wider default rule set reports **34 pre-existing findings** (B019, RUF046,
UP017, DTZ011, S110 …) that the "ruff clean" claims in `STATE.md` were made
against an older version. None are new defects; treat 34 as the floor and only
require that a change adds none.

## Claude Code on the web — sandbox (tested 2026-07-22)

State of the remote environment, and what to change to unblock the season
workflows there.

## What already works (no action needed)

- **Package registries** (PyPI etc.) — dependency install works under any policy.
  The SessionStart hook (`.claude/hooks/session-start.sh`) installs the package
  with `dev`, `models` and `optimize` extras plus `penaltyblog`, so every
  session starts with the full test suite green (29 tests) — no manual setup.
- **github.com / raw.githubusercontent.com** — reachable. The vaastav
  historical dataset and FPL-Core-Insights (backtest gate, PLAN §4) can be
  pulled today.
- **WebSearch** — runs server-side, outside the sandbox egress, so news/rules
  research works even while direct fetches are blocked. WebFetch does NOT
  (it goes through the sandbox proxy and gets the same 403s).

## What is blocked in the sandbox (needs a network-policy change)

The sandbox's egress policy returns 403 for every non-GitHub project domain
(*not* an issue on the local workstation above). Fix: in the environment's
settings on claude.ai/code, either switch to trusted network access or add this
allowlist:

| Domain | Needed for |
|---|---|
| `fantasy.premierleague.com` | FPL API snapshots (`/fpl-refresh`) — **highest priority** |
| `www.football-data.co.uk` | Dixon-Coles training data |
| `www.premierleague.com` | Official fixtures/news |
| `understat.com` | xG rates (later phase) |
| `www.premierinjuries.com` | Injury table (`/fpl-news-sweep`) |
| `www.fantasyfootballscout.co.uk` | Team news, strategy consensus |
| `www.livefpl.net` | Price predictions, EO |
| `fplreview.com` | Projection benchmarks |
| `www.bbc.com`, `www.skysports.com` | Press conferences, team news |
| `www.reddit.com` | r/FantasyPL sentiment |

(Full curated source list with tiers: `config/sources.yaml`.)

## Re-testing after a policy change

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://fantasy.premierleague.com/api/bootstrap-static/
# 200 → unblocked; 000 → still policy-blocked (proxy 403 on CONNECT)
curl -sS "$HTTPS_PROXY/__agentproxy/status"   # recentRelayFailures names blocked hosts
```

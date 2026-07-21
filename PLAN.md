# fpl-claude — Application Plan (v2)

*A Claude-driven Fantasy Premier League manager for the 2026/27 season. Moneyball for FPL:
the market prices reputation; we price expected points per million.*

*Updated July 21, 2026 per owner directives: project renamed **fpl-claude**; built directly
in this repo; **no FPL account connection** (owner submits moves manually — recommend-only);
weekly all-team reports are a first-class deliverable; Twitter/X + web search over curated
FPL strategy pages is part of the core architecture.*

---

## 1. What We're Building

An application where **Claude is the manager** and everything else makes the weekly
decision as informed as possible:

1. A **data platform** ingesting every FPL data point (players, prices, fixtures, results,
   ownership) plus xG, team strength, odds signal, and news/injury intelligence.
2. A **modeling layer** producing expected-points (xPts) projections per player per GW.
3. An **optimization layer** producing optimal squads/transfers/captaincy/chip plans under
   the full FPL ruleset.
4. **Specialized Claude skills** that run analysis and let Claude overlay qualitative
   judgment, writing a reasoned decision memo every gameweek.
5. An **automation layer** (scheduled sessions) for daily scans, weekly team reports,
   pre-deadline runs, post-GW reviews.
6. **Execution: manual by owner.** Every deadline run ends in a decision memo; the owner
   applies it in the FPL app. No credentials, no account access. (Autopilot can be
   revisited later; it is out of scope now.)

**Decision philosophy: models propose, Claude disposes** — documented in every memo.

## 2. Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                 AUTOMATION (scheduled sessions)                    │
│ Mon: team-week reports · daily: refresh+news · T-48h/T-24h/T-2h:   │
│ deadline runs · post-GW: review                                    │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ invokes
┌──────────────────────────────▼─────────────────────────────────────┐
│                     CLAUDE SKILLS (the brain)                      │
│ /fpl-team-week-report  /fpl-news-sweep   /fpl-scout                │
│ /fpl-plan-gameweek     /fpl-chip-strategy /fpl-review /fpl-refresh │
└──────┬───────────────────────┬───────────────────────┬─────────────┘
       │                       │                       │
┌──────▼────────┐   ┌──────────▼─────────┐   ┌─────────▼────────────┐
│ DATA LAYER    │   │ MODEL LAYER        │   │ DECISION LAYER       │
│ FPL API       │   │ minutes model      │   │ MILP (HiGHS)         │
│ FPL-Core-     │   │ team model (DC +   │   │ rules engine (YAML)  │
│  Insights     │   │  odds blend)       │   │ chip planner         │
│ Understat xG  │   │ player xG/xA       │   │ hit-EV policy        │
│ vaastav hist. │   │ → xPts, 8-GW decay │   │ captain EV table     │
│ odds CSVs     │   │ backtest gate      │   │                      │
│ WEB/X SEARCH  │   └────────────────────┘   └──────────────────────┘
│ (sources.yaml)│
└──────┬────────┘
       │
┌──────▼─────────────────────────────────────────────────────────────┐
│ STORAGE: DuckDB + append-only raw JSON/parquet snapshots (db/)     │
│ OUTPUTS: decisions/gw{NN}.md · reports/weekly/{YYYY-WW}/*.md       │
└────────────────────────────────────────────────────────────────────┘
```

Core stack: **Python** (requests, pandas, duckdb; later lightgbm, PuLP+HiGHS, penaltyblog).
[footy-api](https://github.com/flavnat/footy-api) (TS/GraphQL/Postgres FPL wrapper) remains
the candidate base for an optional later dashboard phase — not needed for the core.

## 3. Data Layer

| Source | What | How |
|---|---|---|
| **Official FPL API** (public, read-only) | `bootstrap-static` (players, prices, form, ownership, status/news), `fixtures`, `element-summary/{id}`, `event/{gw}/live` | `src/fpl_claude/data/fpl_api.py`, snapshotted daily |
| **FPL-Core-Insights** | Best actively-updated FPL dataset (FPL API + match stats + Club Elo, FPL-ID-keyed) | CSV pulls |
| **vaastav/Fantasy-Premier-League** | History 2016-17 → 2024-25 for training/backtests | one-time load |
| **Understat** | Player xG/xA per 90 (post-2025-API-change client) | weekly |
| **Odds** | football-data.co.uk CSVs → clean-sheet/goals market signal | weekly |
| **Other competitions** (UCL/UEL/UECL, FA Cup, EFL Cup) | Fixtures/results for congestion tracking — FPL API only covers PL | football-data.org free tier + web search in skills |
| **Web + X search** (see `config/sources.yaml`) | Injuries, press conferences, lineup leaks, strategy/community consensus, price predictions | WebSearch/WebFetch inside skills. No paid X API — X content reached via web search. |
| **ID mapping** | FPL ↔ Understat ↔ FBref | seeded from FPL-Core-Insights |

Storage: DuckDB + append-only snapshots so backtests only ever use point-in-time data.

## 4. Model Layer (build order = importance)

1. **Minutes model** — P(start)/P(60+)/P(cameo): rolling starts, rotation vs congestion
   (European weeks!), flags, price signals, post-WC-2026 fatigue. LightGBM on vaastav history.
2. **Team model** — penaltyblog Dixon-Coles blended with bookmaker odds → expected goals
   for/against, clean-sheet probabilities per fixture.
3. **Player event model** — per-90 xG/xA × team share × opponent adj → expected
   goals/assists/CS/saves/defensive-contribution + BPS proxy.
4. **xPts aggregation** — scoring-rule mapping per position; 8-GW horizon, ~0.85/GW decay.
5. **Backtest gate (non-negotiable):** point-in-time backtests on 2023/24–2025/26; must
   beat template baseline in full-season simulation before going live.

References (researched & verified): OpenFPL (per-position ensembles, warm start candidate),
AIrsenal (architecture reference), bpl-next (Bayesian alternative), open-fpl-solver (MILP formulation).

## 5. Decision Layer

- **MILP optimizer** (PuLP + HiGHS): squad/XI/captain/vice/bench-order/transfers/chips over
  rolling 8-GW horizon; objective = decayed xPts − 4×hits.
- **Rules engine — config-driven** (`config/rules/2026-27.yaml`): budget, squad shape, 3-per-club,
  formations, transfer banking, chip inventory/windows, scoring incl. defensive contributions.
  FPL changes rules yearly → every rule carries a `verify_at_season_launch` flag and we
  reconcile against the official site before GW1.
- **Policies:** hits only above EV threshold (default +4.5 over horizon); captain from EV
  table with ceiling/floor; flagged players need a written plan; T-2h final check falls back
  to last approved plan. **A legal submission must always be derivable from cached data —
  missing a deadline is the only unforgivable failure.**
- **Chip planner:** DGW/BGW detection via fixture-diff monitoring; season chip calendar.

## 6. Skills

| Skill | Job | Cadence |
|---|---|---|
| `/fpl-refresh` | Run pipelines, validate freshness, snapshot | Daily |
| `/fpl-team-week-report` | **The weekly flagship: a report on every PL team** — all matches played that week in every competition (PL, UCL, UEL, UECL, domestic cups), minutes distribution, injuries picked up/cleared, press-conference notes, congestion next 14 days, rotation-risk implications for FPL assets. Output: `reports/weekly/{YYYY-WW}/{team}.md` + an index with the week's biggest FPL takeaways. | Every Monday + after midweek rounds |
| `/fpl-news-sweep` | Sweep `sources.yaml` (web + X via search): injuries, pressers, leaks, strategy-page consensus, price predictions → structured risk table | Daily + pre-deadline |
| `/fpl-scout` | Shortlists: xPts/£, differentials (low ownership × high projection), template drift, price radar | Weekly |
| `/fpl-plan-gameweek` | refresh → news sweep → models → optimizer → Claude overlay → **decision memo** `decisions/gw{NN}.md` for the owner to apply manually | T-48h, T-24h, final T-2h |
| `/fpl-chip-strategy` | Chip calendar upkeep on fixture changes | Weekly |
| `/fpl-review` | Post-GW retro: predicted vs actual, luck vs process, calibration log, rank tracking | Post-GW |

## 7. Automation

Scheduled cloud sessions: Monday team-week reports; daily refresh + news sweep (~09:00 UTC);
deadline runs at T-48h/T-24h/T-2h (deadline calendar from FPL API); post-GW review.
Each run ends with committed markdown outputs and a notification to the owner — who then
makes the moves in the FPL app manually.

## 8. Repo Structure (this repo)

```
Projects/
├── CLAUDE.md                     # persona: expert football manager, Moneyball rules
├── .claude/skills/fpl-*/         # the 7 skills
└── fpl-claude/
    ├── PLAN.md                   # this file
    ├── README.md
    ├── pyproject.toml
    ├── config/
    │   ├── rules/2026-27.yaml    # FPL ruleset (verify at season launch)
    │   └── sources.yaml          # curated web/X sources
    ├── src/fpl_claude/
    │   ├── data/                 # fpl_api.py, snapshot.py (+ understat, insights, odds later)
    │   ├── models/               # minutes, team_dc, xpts (Phase 2)
    │   ├── optimize/             # milp.py (Phase 3)
    │   ├── rules/                # engine.py — YAML ruleset loader
    │   └── reports/              # team_week.py — weekly report builder
    ├── decisions/                # gw01.md … gw38.md (season audit trail)
    ├── reports/weekly/           # {YYYY-WW}/{team}.md
    ├── db/                       # DuckDB + raw snapshots (gitignored except schema)
    ├── notebooks/                # backtests, validation
    └── tests/
```

## 9. Build Phases (GW1 ≈ mid-August 2026)

| Phase | When | Deliverable |
|---|---|---|
| **0. Scaffold** ✅ | Now | This structure, FPL API client, snapshotting, rules YAML, sources YAML, skills, first team-week report dry run |
| **1. Data** | Week 1–2 | All pipelines live; historical data loaded; ID mapping |
| **2. Models** | Week 2 | Minutes + team + player models; backtest gate passed |
| **3. Optimizer** | Week 2–3 | MILP + rules engine + policies; GW1 draft squad with EV analysis |
| **4. Skills live** | Week 3 | Full `/fpl-plan-gameweek` dry run; chip calendar v1; weekly reports in steady state |
| **5. Automation** | Week 4 (pre-GW1) | Scheduled sessions armed; recommend-mode for GW1 |
| **6. Optional dashboard** | In-season | footy-api-based serving layer if wanted |

## 10. The Season Goal

Suggested `/goal` once live:

> **/goal** Manage the fpl-claude FPL team for the entire 2026/27 season and maximize final
> overall rank — top 1% minimum, top 10k stretch. Every week: publish the all-team weekly
> report (every competition, injuries, congestion); every gameweek without exception run
> the full pipeline (refresh → news sweep → models → optimizer → decision memo in
> decisions/) in time for the owner to apply moves manually before the deadline; publish a
> post-GW review with calibration. Never miss a deadline window, never recommend a flagged
> player without documented reasoning, never take a hit below the EV threshold, keep the
> chip calendar current.

Honest framing: outright #1 of ~11M is a variance lottery; top 1% is very achievable and
top 10k is elite. The process goals above are what we control — Moneyball says judge the
process, and the rank follows.

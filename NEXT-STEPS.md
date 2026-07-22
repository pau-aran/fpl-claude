# Next Steps — road to GW1 (deadline ≈ mid-August 2026)

*Status as of 2026-07-22. The code side is essentially done: data plumbing, xPts v1
(minutes + Dixon-Coles + rules-driven scoring), price radar, MILP optimizer — all
offline-tested (28 tests). What remains is gated on **network access** and on the
**2026/27 season opening**, not on engineering.*

## 1. First live data run — NEEDS a networked session (or run locally)

The cloud sandbox used so far only reaches package registries. From any
environment that can reach the internet, from `fpl-claude/`:

```bash
pip install -e ".[dev,optimize]"
pip install penaltyblog --no-deps && pip install scipy tqdm pulp networkx matplotlib plotly ipywidgets

python -m fpl_claude.data.fpl_api snapshot          # first real 2026/27 snapshot
python -m fpl_claude.data.snapshot                  # build the DuckDB
python -m fpl_claude.data.football_data fetch 2425 2526   # Dixon-Coles training data
python -m fpl_claude.models.projections             # first real projections run
python -m fpl_claude.data.prices --from-snapshot <today>  # price radar
```

Sanity checks on that first run: promoted-team names map cleanly (extend
`TO_FPL_NAME` in `data/football_data.py` if not), `team_model` column says
`dixon_coles` not `fdr_fallback`, and pre-season projections lean on
`--prior-snapshot` (grab the last 2025/26 bootstrap from vaastav or
FPL-Core-Insights if we never snapshotted it ourselves).

## 2. Backtest gate (PLAN §4 — non-negotiable, before GW1)

- Load vaastav 2016–25 history + FPL-Core-Insights; seed the FPL↔Understat ID map.
- Point-in-time backtests of xPts v1 on 2023/24–2025/26 vs the template baseline.
- Pass → xPts numbers may drive memos (drop the "ungated" label).
  Fail → pull in OpenFPL per-position ensembles as the warm start (the decision
  we deferred; see PLAN §4 table) and re-gate.

## 3. Season-launch rules verification (the day the 2026/27 game opens)

- Reconcile every `verify_at_season_launch` section of `config/rules/2026-27.yaml`
  against https://fantasy.premierleague.com/help/rules — chip counts/windows
  (did the two-sets-per-half format survive? assistant manager back?), transfer
  banking cap, defensive-contribution thresholds, prices/budget.
- Set `verified_against_official: true` and clear the flags; the optimizer
  refuses real runs until this is done (`allow_unverified` is for dry runs only).

## 4. GW1 build (once 1–3 are done)

- `/fpl-plan-gameweek` end-to-end: refresh → news sweep → projections →
  optimizer initial-build mode → Moneyball overlay → `decisions/gw01.md`.
- Post-WC-2026 edge to encode as minutes overlays: late returners, early rotation.
- Chip calendar v1 via `/fpl-chip-strategy`.

## 5. Automation (final pre-GW1 week)

Scheduled sessions per PLAN §7: daily refresh + news sweep (~09:00 UTC), Monday
team-week reports, T-48h/T-24h/T-2h deadline runs, post-GW review. Each run ends
in committed markdown + owner notification; owner applies moves manually.

## Engineering backlog (not GW1-blocking)

- Phase 3b: multi-period transfer path + chip planning in the MILP.
- Minutes v2: LightGBM on vaastav history (congestion, Euro-week features).
- Odds blend into the team model; Understat rates into `models/rates.py`.
- `/fpl-review` calibration loop wired to `db/projections/` CSVs.

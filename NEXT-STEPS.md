# Next Steps — road to GW1 (deadline ≈ mid-August 2026)

*Status as of 2026-07-22. The code side is essentially done: data plumbing, xPts v1
(minutes + Dixon-Coles + rules-driven scoring), price radar, MILP optimizer — all
offline-tested (28 tests). What remains is gated on **network access** and on the
**2026/27 season opening**, not on engineering.*

## 1. First live data run — NEEDS a networked session (or run locally)

The cloud sandbox's egress policy blocks the FPL API and football-data.co.uk
(see `docs/environment.md` for the tested state and the allowlist to grant).
GitHub IS reachable, so the vaastav/FPL-Core-Insights pulls in §2 work today,
and WebSearch works for news/rules research. Dependencies are no longer a
manual step — `.claude/hooks/session-start.sh` installs everything at session
start. From any environment that can reach the internet, from the repo root:

```bash
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

## 2. Backtest gate (PLAN §4 — non-negotiable, before GW1) — PASSED ✅

The 2025/26 GW1–10 season replay is COMPLETE (`src/fpl_claude/backtest/`,
artifacts in `reports/backtest/2025-26/`, verdict in `VERDICT.md`):
**624 pts vs the 531 average-manager baseline (+93)**, strictly point-in-time,
1 hit all season, captaincy 10/10. Beat the field in 7/10 weeks; back half
(GW6–10) +68 as the pipeline matured. On a **top-1% trajectory** (+9.3/GW over
average; exact rank an honest estimate — top-10k tier totals weren't
retrievable, see baseline.md/VERDICT.md). The "ungated" label is DROPPED.

The loop shipped six model/policy fixes (rates shrinkage, team-model sample
floor, DC phantom prior, marginal-net hit gate, duration-scoped overlays, and
the newcomer confidence haircut) and grew the decision architecture (manager
overlay, plan.md path discipline, community consensus input, the purist
positional-duel lens).

Defects found in the backtest — now RESOLVED for the LIVE pipeline (this
branch, `claude/branch-analysis-optimization-n8q1f5`):
- **[DONE] Bench-order fixture softness** (was the biggest recurring leak: GW10
  −3, GW13 −8). Split fix: the optimizer now picks XI/captain/vice/bench on the
  nearest `xpts_gw{n}` (single-GW) column, not the decayed horizon it buys the 15
  on (`milp.py` `_pick_lineup`, auto-detected) — fixes GW10; and a manager
  `start`/`bench` XI override (`ManagerDecision`, decision JSON) catches the GW13
  class the stats model can't see (depleted opponent defence). Skills updated
  (plan-gameweek overlay, review bench-miss check).
- **[DONE] Minutes p_start=1.0 for no-prior players** — `_start_share` now shrinks
  the no-prior tiny sample toward `NEUTRAL_START_SHARE` by `team_games/3`;
  de-risks GW1–3 of the post-WC season.
- **[DONE/process] Level calibration** — decided NO model change (never flipped a
  pick, cancels in the hit-gate); `/fpl-review` now logs the captain slot
  separately so EV reporting reads against the known captain-slot variance.
- **[DONE/process] Suspension verification** — `/fpl-news-sweep` now requires the
  offence AND confirmation the ban is served, and defaults to AVAILABLE on
  ambiguity; plus a two-consecutive-0-minute minutes red-alert.
- Optional depth later: extend to 2023/24–2024/25 replays for more calibration
  seasons; seed the FPL↔Understat ID map for Minutes v2; a same-club/same-fixture
  sub-1pt "phantom swap" surfacing filter (ergonomics only — the lock already
  neutralises it).

Shipped after the gate (re-ran the GW1–10 replay at parity — 659=659, no committed
decision changed, so no regression; see docs/external-repo-review-x402-fpl-api.md):
- **Set-piece / penalty-duty signal.** `xpts.py` gains a `penalty` component for
  the designated taker (`penalties_order==1`), double-count-guarded: it credits
  only the pens a player's `xg90` cannot already embed (a priorless newcomer taker,
  decaying as his own minutes accrue) plus an explicit overlay `pen_boost` for a
  mid-season duty change. Projections expose `is_pen_taker` / `is_set_piece_taker`.
  The backtest can't exercise the forward-looking edge (its taker order is static
  season-end), so this is a live-value add proven safe, not proven profitable —
  its payoff shows up when a taker actually changes.
- **`ep_next` benchmark.** FPL's own next-GW expected points now rides along as a
  projections column — a free external predictor for /fpl-review calibration and a
  captaincy sanity check. Never a model input; NaN in the backtest (no honest
  point-in-time value in the archive).

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

*Full prioritized list with buildable-now vs blocked split: `NEXT-STEPS-IMPLEMENTATION.md`.*

- Phase 3b: **chip MECHANICS DONE** (backtest simulator plays/scoring WC/FH/BB/TC, one-per-half
  inventory, validated by the AFCON counterfactual). Remaining 3b: automatic chip-TIMING in the
  decision layer (DGW/BGW detection + chip-EV surface) and the multi-period transfer path.
- Minutes v2: LightGBM on vaastav history (congestion, Euro-week features).
- Odds blend into the team model; Understat rates into `models/rates.py`.
- `/fpl-review` calibration loop wired to `db/projections/` CSVs.

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

Defects found, carried to the LIVE pipeline (VERDICT.md + reviews/gw10.md §4):
- **[OPEN] Level calibration** — model under-predicts totals ~15–25% in strong
  weeks (ranking unaffected; an EV-reporting/hit-gate issue). Fix: an
  environment-level calibration term and/or better captain-ceiling + bonus
  modelling.
- **[OPEN] Bench-order ignores fixture softness** — weight FDR/CS probability
  in XI ordering, or expose a manager bench-order override.
- **[PROCESS] Suspension verification** — confirm a ban was actually
  upheld/served against the team sheet; default AVAILABLE on ambiguity.
- Optional depth later: extend to 2023/24–2024/25 replays for more calibration
  seasons; seed the FPL↔Understat ID map for Minutes v2.

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

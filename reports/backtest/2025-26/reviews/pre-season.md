## Pre-season engineering (found while building the harness, before GW1)

- **Rates explosion on tiny samples** — 1 minute + 0.06 xG projected as a
  5.4 xG/90 captain pick (Mheuka). Fix: pseudo-minute shrinkage in
  `models/rates.py` (`SHRINKAGE_MINUTES = 90`). Applies to the live pipeline.
- **Dixon-Coles trusted 1-match teams** — promoted Sunderland's opening 3-0
  produced a rating that captained their £4.6m defender with +50 "EV". Fix:
  `MIN_TEAM_MATCHES = 5` coverage floor in `models/team.py`, FDR fallback
  below it. Applies to the live pipeline (matters every promoted-team season).
- **End-of-season files leak January transfers** — vaastav `players_raw.csv`
  team/position are final-state; point-in-time values must come from
  `merged_gw` rows at-or-before the GW. Backtest-only, but a warning for any
  future historical training data (Minutes v2).

---

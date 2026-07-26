# Backtests & calibration notebooks (Phase 2+)

| file | what it is |
|---|---|
| `calibration_analysis.py` | The closed 20-GW backtest decomposition (defect A2). Pure post-hoc analysis of the committed `reports/backtest/2025-26/gwNN_players.csv`, importing no pipeline code so it stays reproducible verbatim: `PYTHONPATH=src python notebooks/calibration_analysis.py`. Regenerates every table in `reports/backtest/2025-26/calibration.md`. |
| `calibration.md` | The **append-only live log** — one section per gameweek, written by `/fpl-review` step 5 via `python -m fpl_claude.reports.calibration --gw N`. Predicted side from a pre-deadline `db/projections/` snapshot, actual side from the FPL API (or a backtest archive), joined on the FPL player id. Never edit or reorder past sections. |

Both use the same error convention (`error = actual − predicted`), the same
population-std / sample-SE t-test, and the same base-XI-vs-captain-slot split, so
a live week reads directly against the 20-GW backtest study.

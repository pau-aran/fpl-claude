---
name: fpl-refresh
description: Refresh all fpl-claude data — snapshot the FPL API (players, prices, fixtures, flags), rebuild the DuckDB, and report what changed since the last snapshot (price moves, new flags, ownership swings). Run daily or before any analysis.
---

# Data Refresh

1. From the repo root:
   ```bash
   python -m fpl_claude.data.fpl_api snapshot
   python -m fpl_claude.data.snapshot
   python -m fpl_claude.data.prices --from-snapshot <today>
   ```

2. Diff against the previous snapshot date (query the DuckDB `players` table across
   `snapshot_date`) and report:
   - actual price rises/falls since last snapshot (the prices CLI prints them)
   - **price radar**: top transfer-pressure risers/fallers — anyone on our squad,
     shortlists, or planned transfers who is close to a move gets named; sanity-check
     the ranking against FPL Statistics (sources.yaml) before asserting urgency
   - new or cleared flags (`status`, `news`, `chance_of_playing_next_round`)
   - biggest ownership and transfer-in/out swings
   - next deadline (`fpl_claude.data.fpl_api.next_deadline()`)

3. If anything materially affects our current squad or shortlists, say so explicitly
   at the top of your summary ("ACTION SIGNAL:" prefix).

Phase 1 additions (when built): FPL-Core-Insights pull, Understat xG refresh,
odds CSVs. Extend this skill then.

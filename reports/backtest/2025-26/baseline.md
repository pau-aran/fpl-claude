# 2025/26 Backtest Baseline — Official FPL Averages, GW1-14

Benchmark for the fpl-claude backtest: the official average manager score per gameweek
(the "Average" shown on the FPL site), plus the official highest GW score, for
gameweeks 1-10 of the 2025/26 season.

**Primary source:** [olbauday/FPL-Core-Insights](https://github.com/olbauday/FPL-Core-Insights)
(`data/2025-2026/gameweek_summaries.csv`, commit `768e386`, 2026-07-02) — a mirror of the
official FPL API `bootstrap-static` events feed (`average_entry_score`, `highest_score`).
Values cross-verified against independent web sources where snippets were available
(see verification notes below the table).

| GW | Overall average | Highest GW score | Top-10k average | Notes / source |
|----|-----------------|------------------|-----------------|----------------|
| 1  | 54 | 127 | not found | Deadline 2025-08-15. Verified twice: FPL API mirror + FPL Dave "GW1 Review: 54pts Average" (highest 127). |
| 2  | 51 | 140 | not found | Deadline 2025-08-22. FPL API mirror. (A substack claim of 56/146 traced to an earlier season and was discarded.) |
| 3  | 48 | 118 | not found | Deadline 2025-08-30. FPL API mirror. Pre-international-break GW (Liverpool 1-0 Arsenal; Brighton 2-1 Man City). |
| 4  | 63 | 139 | not found | Deadline 2025-09-13. Verified twice: FPL API mirror + FPL Dave "GW4 Review: 63pts Average". Highest early-season average. |
| 5  | 42 | 112 | not found | Deadline 2025-09-20. FPL API mirror. Lowest of the first ten GWs. |
| 6  | 46 | 124 | not found | Deadline 2025-09-27. FPL API mirror. |
| 7  | 60 | 135 | not found | Deadline 2025-10-03. FPL API mirror. Haaland (5.5M captains) scored winner at Brentford; Salah blanked again (premierleague.com GW7 stats). |
| 8  | 56 | 138 | not found | Deadline 2025-10-18. FPL API mirror. First GW after October international break. |
| 9  | 46 | 124 | not found | Deadline 2025-10-24. FPL API mirror. |
| 10 | 65 | 135 | not found | Deadline 2025-11-01. FPL API mirror. Highest average of GW1-10. |
| 11 | 38 | not found | not found | Deadline 2025-11-08. Verified: AllAboutFPL "lowest of the season so far" + FPL API mirror. City 3-0 Liverpool; Villa 4-0 Bournemouth; two league-wide penalty misses on the slate. |
| 12 | 39 | 134 | not found | Deadline 2025-11-22. Verified: [FPL Dave GW12 review](https://www.fpldave.com/gameweek/12) ("39pts Average") + FPL API mirror. First GW after the November int'l break — Gabriel/Semenyo among the break's injuries. |
| 13 | 35 | 123 | not found | Deadline 2025-11-29. FPL API mirror (olbauday gameweek_summaries.csv, re-fetched). Low slate — two top-six H2Hs (CHE-ARS, CRY-MUN) cancelled template returns; Haaland blanked at home to Leeds. |
| 14 | 58 | 138 | not found | Deadline 2025-12-02 (midweek). FPL API mirror. Bounce-back slate — Haaland's captaincy drought ended (home... away at Fulham). |

**Average-manager 14-GW cumulative total (sum of official GW averages): 701 points.**

*Look-ahead (fetched, not yet played in-sim): GW15 avg 49, GW16 60, GW17 66.*

## Verification notes

- The dataset's `average_entry_score` / `highest_score` columns were cross-checked against
  five independently published values, all exact matches:
  - GW1: 54 avg / 127 highest — [FPL Dave GW1 review](https://www.fpldave.com/gameweek/1)
  - GW4: 63 avg — [FPL Dave GW4 review](https://www.fpldave.com/gameweek/4)
  - GW11: 38 avg ("lowest of the season so far") — AllAboutFPL search snippet
  - GW12: 39 avg — [FPL Dave GW12 review](https://www.fpldave.com/gameweek/12); GW20: 42 avg — [FPL Dave GW20 review](https://www.fpldave.com/gameweek/20)
  - GW34: 36 avg / 114 highest and GW36: 65 avg / 145 highest — [FPL Pulse GW34](https://www.fplpulse.com/blog/fpl-gameweek-34-review-2025) / [GW36](https://www.fplpulse.com/blog/fpl-gameweek-36-review-2025) reviews
- **Top-10k averages: not found.** livefpl.net historical tier averages (the usual source)
  were not indexed in searchable form and direct fetching was blocked in this environment;
  no per-GW top-10k figure could be verified, so the column is marked "not found"
  rather than guessed. Two stray snippet claims (top-10k 47 in GW2/GW3) could not be
  attributed to a concrete page and were excluded.
- `ranked_count` at GW10 was ~12.28M managers (from the same dataset), for context on
  what "average" covers.
- Raw extract kept in the session scratchpad; the dataset repo can be re-cloned at any
  time to reproduce (file: `data/2025-2026/gameweek_summaries.csv`).

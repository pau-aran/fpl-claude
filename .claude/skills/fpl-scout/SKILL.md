---
name: fpl-scout
description: Moneyball scouting — build position-by-position shortlists ranked by expected points per million, find differentials (low ownership × high projection), track template drift and price pressure. Run weekly or when the user asks who to buy/watch.
---

# Scout

You are fpl-claude. The market buys reputation; we buy points per million.

1. Refresh data (`/fpl-refresh` steps) if the last snapshot is older than today.

2. Run the projections pipeline:
   `python -m fpl_claude.models.projections --from-snapshot <latest>` (add
   `--prior-snapshot` early season, `--overlays` if the news sweep produced minutes
   overrides). It writes the ranked table to `db/projections/`. Check the
   `team_model` column — if it says `fdr_fallback`, fetch results first
   (`python -m fpl_claude.data.football_data fetch 2526 2627`) and rerun.
   NOTE: until the backtest gate (PLAN §4) has passed, label all numbers
   "xPts v1 (ungated)".

3. From that table build, per position (GKP/DEF/MID/FWD):
   - **Value board:** rank by `xpts_per_m`; exclude `low_sample` or
     sub-~0.7 `p_start` players without a written exception.
   - **Differentials:** selected_by_percent < 10% × high `xpts_horizon`.
   - **Template:** selected_by_percent > 30% — we must own a reason NOT to own them.

4. **Consensus cross-check (mandatory before publishing):** compare our top ~5 per
   position against at least two public sources (LiveFPL, FPL Review free numbers,
   FFScout picks — see sources.yaml). Where we diverge hard (a player we rate that
   consensus ignores, or vice versa), investigate before publishing: usually it's
   minutes news our snapshot missed — fix via overlay; sometimes it's the market
   mispricing — that's the edge, write it up. Never silently copy consensus:
   benchmark, not input.

5. Enrich the top candidates with a quick web check (sources.yaml): role security,
   set-piece duties, penalty taking, new-signing minutes ramp.

6. Output: one table per position (player, price, ownership, xPts/£m, verdict
   BUY/WATCH/AVOID + one-line rationale), then a "**Differential of the week**" and
   "**Trap of the week**" (the popular pick the data says to fade).

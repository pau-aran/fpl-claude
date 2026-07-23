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

3. From that table build, per position (GKP/DEF/MID/FWD):
   - **Value board:** rank by `xpts_per_m`; exclude `low_sample` or
     sub-~0.7 `p_start` players without a written exception.
   - **Bench economics:** the 2nd GK is a dead slot most weeks — shortlist the
     cheapest viable option, don't spend up. For the last outfield bench slot,
     when candidates are otherwise equal, prefer the one whose fixtures
     COMPLEMENT an existing bench piece across GWs (bench rotation). Strict
     tie-breaker only — never over XI quality.
   - **Differentials:** selected_by_percent < 10% × high `xpts_horizon`.
   - **Template:** selected_by_percent > 30% — we must own a reason NOT to own them.
   - **Set-piece edge:** the `is_pen_taker` / `is_set_piece_taker` columns flag
     designated takers — a durable, minutes-adjacent value signal the crowd is
     slow to reprice. A newly-installed penalty taker (his xg90 lags his new
     duty) is a live buy signal; prioritise takers on the value board.
   - **Sanity vs FPL:** the `ep_next` column is FPL's own next-GW expected
     points — a free external benchmark. Flag any candidate where our
     `xpts_gwNN` and `ep_next` disagree hard for a look before publishing.

4. **Consensus cross-check (mandatory before publishing):** compare our top ~5 per
   position against at least two public sources (LiveFPL, FPL Review free numbers,
   FFScout picks — see sources.yaml). Where we diverge hard (a player we rate that
   consensus ignores, or vice versa), investigate before publishing: usually it's
   minutes news our snapshot missed — fix via overlay; sometimes it's the market
   mispricing — that's the edge, write it up. Never silently copy consensus:
   benchmark, not input.

5. Enrich the top candidates with a quick web check (sources.yaml): role security,
   set-piece duties, penalty taking, new-signing minutes ramp. When the web
   confirms a penalty-duty CHANGE the snapshot's order hasn't caught yet, encode
   it as an overlay `pen_boost` (0–1, see fpl-news-sweep) so the projection
   prices the new taker's spot-kicks instead of waiting weeks for xg90 to catch up.

6. **Price radar** (`python -m fpl_claude.data.prices --from-snapshot <latest>`):
   note which BUY/WATCH candidates are near a rise (buy-early candidates) and which
   of our own players are near a fall (sell-timing risk). Price pressure may move
   a decision's *timing* within the window — it never changes *who* we buy or sell;
   any memo that acts on price says so explicitly.

7. Output: one table per position (player, price, ownership, xPts/£m, verdict
   BUY/WATCH/AVOID + one-line rationale), then a "**Differential of the week**",
   a "**Trap of the week**" (the popular pick the data says to fade), and a
   "**Price watch**" line (imminent rises/falls that affect us).

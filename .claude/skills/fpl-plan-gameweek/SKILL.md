---
name: fpl-plan-gameweek
description: The main decision pipeline — refresh data, sweep news, run projections and the optimizer (when built), apply the Moneyball overlay, and write the gameweek decision memo (transfers, XI, captain, chip, EV, risks) for the owner to apply manually in the FPL app. Run at T-48h, T-24h, and a final T-2h check before each deadline.
---

# Plan Gameweek

You are fpl-claude. The output is `decisions/gw{NN}.md` — the owner
applies it manually; you never touch their FPL account.

## Pipeline

1. **Refresh:** run /fpl-refresh steps; confirm next deadline via
   `fpl_claude.data.fpl_api.next_deadline()`. State time remaining.
2. **News:** run /fpl-news-sweep — the risk table goes into the memo.
3. **Project:** run the pipeline —
   `python -m fpl_claude.models.projections --from-snapshot <today>` with
   `--overlays` built from the news sweep (each override = player id, start_share,
   written reason) and `--prior-snapshot` early season. Until the backtest gate
   (PLAN §4) passes, label all numbers "xPts v1 (ungated)". Then the **consensus
   cross-check**: compare our captain top-3 and every transfer-in candidate against
   at least two public sources (LiveFPL, FPL Review free, FFScout). Big divergence →
   investigate (stale minutes intel? fix overlay and rerun) and record the verdict
   in the memo's "Consensus check" line. Benchmark, never input.
4. **Optimize:** run the MILP (`fpl_claude.optimize.milp.optimize`) on the
   projections table — initial-build mode for GW1/wildcard, transfer mode
   (CurrentSquad with buy costs, bank, free transfers) otherwise. It refuses
   while the ruleset is unverified: before season-launch verification pass
   `allow_unverified=True` and label the memo "rules unverified — dry run".
   Quote its `ev_delta` against `policies.hit_ev_threshold` for any hit.
5. **Overlay (the part only you can do):** deviate from the optimizer only with a
   written reason (presser tone, rotation pattern from the weekly report, tactical
   change). Check every recommended player against the risk table — a flagged
   player needs a documented plan. Include the **positional-duel read** (owner
   directive, 2026-07-22): name the in-form players facing a weak direct
   counterpart this GW (winger vs slow/exposed fullback, striker vs error-prone
   or stand-in CBs, attacking fullback vs a non-tracking winger, defence/GK vs a
   blunt attack) — team FDR hides soft individual duels. Use it to seed
   shortlists the model underrates and to tilt close calls (captaincy tiebreak,
   near-equal targets, bench order); it never overrides the EV gate, the plan,
   or minutes risk. Write the named duel into the memo so the review can grade it.
6. **Policies:** hits only if EV gain > `policies.hit_ev_threshold`; captain from
   an EV table (show top 3 with ceiling/floor); respect chip calendar. Price
   pressure (from the refresh radar) may pull a decided transfer earlier in the
   window or delay a sale — it never changes WHO we buy or sell, and acting
   early forfeits the T-2h flag check, so weigh £0.1 against late team news
   and write the trade-off down. Sell prices via `Ruleset.sell_price()`.

## Memo format (`decisions/gw{NN}.md`)

- **Header:** GW, deadline (UTC + time remaining), squad value, bank, free transfers.
- **Transfers:** OUT→IN with EV delta and rationale; hits justified against threshold.
- **XI + bench order + captain/vice:** captain EV table.
- **Chip decision:** use/hold, vs the calendar.
- **Risk table** (from news sweep) + what we're deliberately fading (the template
  deviation and why).
- **Consensus check:** one line per divergence from public projections and our
  verdict (our edge vs our miss).
- **Plan B:** the fallback if a flagged player is ruled out at T-2h.
- Commit the memo. At T-2h: re-verify flags only; if nothing changed, confirm the
  memo stands ("FINAL"); if something changed, apply Plan B, mark the edit, commit.

Never let the deadline pass without a FINAL memo — a legal recommendation from
cached data always beats silence.

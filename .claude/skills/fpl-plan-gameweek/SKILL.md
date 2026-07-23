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
4b. **Manager's Read — write it BEFORE you read the solve (co-equal voice, owner
   directive 2026-07-23).** The optimizer is one input, not the anchor; anchoring to
   the machine and rationalising afterward is the failure mode this prevents. In a few
   sentences, put down the HUMAN read: team trajectory / eye-test (manager-bounce sides,
   teams visibly clicking, players who look dangerous before the returns show, Christmas-
   congestion rotation feel, a squad gone thin/over-reliant), who's genuinely due vs cold,
   and who you'd want to watch live. Lean hardest into **team-trajectory/eye-test** and
   **captaincy bravery** (owner emphasis). One feeder of this read is the **positional-duel
   lens**: name the in-form players facing a weak direct counterpart this GW (winger vs
   slow/exposed fullback, striker vs error-prone or stand-in CBs, attacking fullback vs a
   non-tracking winger, defence/GK vs a blunt attack) — team FDR hides soft individual duels.

5. **Reconcile the read with the optimizer.** The Manager's Read carries REAL authority on
   the axes where models are weakest and feel is strongest — **bench order, captaincy,
   differentials-for-rank, riding-vs-fading runs** — and MAY override the solve there even
   against MODEST EV, provided it fits the plan and minutes are safe. It does NOT override:
   a flagged/benched-for-minutes player (the minutes gate is sacred — check every recommended
   player against the risk table), the plan's funding arithmetic, or a LARGE EV gap (the model
   still governs the big quant calls). Every deviation gets a written reason; every named read
   (trajectory call, brave captain, duel) goes into the memo so the review GRADES it — process,
   not outcome — and we measure over the season whether the human overlay adds or leaks points.
6. **Policies:** hits only if EV gain > `policies.hit_ev_threshold`; captain from
   an EV table (show top 3 with ceiling/floor); respect chip calendar. Price
   pressure (from the refresh radar) may pull a decided transfer earlier in the
   window or delay a sale — it never changes WHO we buy or sell, and acting
   early forfeits the T-2h flag check, so weigh £0.1 against late team news
   and write the trade-off down. Sell prices via `Ruleset.sell_price()`.

## Memo format (`decisions/gw{NN}.md`)

- **Header:** GW, deadline (UTC + time remaining), squad value, bank, free transfers.
- **Manager's read (write first):** the human take — team trajectory / eye-test, who's
  due/cold, the named duel(s), any brave-captain or bench-order call and its thesis. Flag
  which calls DEVIATE from the solve so the review can grade the human overlay.
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

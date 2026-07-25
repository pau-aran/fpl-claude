---
name: fpl-fixture-planner
description: Multi-gameweek fixture-run planning — read the next 4-6 GWs per club, spot runs turning good/bad, plan transfer paths 2-3 weeks ahead instead of reacting one GW at a time, and stage the manager overlay (lock/ban) around them. Run before every transfer decision and whenever fixtures change.
---

# Fixture planner

You are fpl-claude. Transfers buy RUNS of fixtures, never one gameweek.
The horizon objective already decays future GWs — this skill is the HUMAN
half: reading the runs, planning paths, and writing the reasoning down.

1. Build the outlook table — next 5 GWs per club with home/away and FDR.
   - Live pipeline: from the latest fixtures snapshot in `db/raw/`.
   - Backtest: `SeasonStore.fixture_outlook(gw)` (already wired into the
     backtest memos and `--propose` output).

2. Classify every club's run, from the perspective of players we own or shortlist:
   - **Turning good** (≥3 of next 5 at FDR ≤ 2, or leaving a hard patch):
     buy-ahead candidates — get in ONE GW BEFORE the run starts, before the
     price and ownership move — UNLESS that entry GW is the target's single
     worst fixture of the run. Then defer one week: you capture the same run at
     a softer entry and bank an FT (GW9 deferred Mateta off ARS(A): 2=2 zero
     cost, banked the FT for the green GW10 +7). Never pay a hit or eat a bad
     entry week for an edge that lives later in the run.
   - **Turning bad** (≥3 of next 5 at FDR ≥ 4, or a derby/top-six gauntlet):
     sell-ahead candidates — plan the exit while value is high; never hold a
     fading run out of inertia.
   - **Split runs** (good now, bad soon): fine for XI now, note the exit GW
     in the plan so the sale is scheduled, not improvised.
   - **International-tournament cliffs** (AFCON from GW17 2025/26; World Cup
     returnees early-season): before buying any mid/fwd, check whether he's in
     an in-season tournament squad and price the gap — a great run that ends at
     a cliff is worth less than its FDR shows. Hold an owned tournament-bound
     asset through his good pre-cliff fixtures, then rotate into a
     non-tournament replacement at the last good GW (GW16 Mbeumo), never sell
     early. Never buy a mid/fwd about to vanish without pricing the gap.
   - **No churn:** never re-buy a player you sold within the last few GWs
     without genuinely NEW information — it admits the sale was wrong and pays
     the buy/sell spread twice (GW3 Wood buy-back veto).

3. Plan transfer PATHS, not moves: with 1 FT/GW and banking to 5, write the
   2-3 week sequence ("bank this week → double-move into X+Y before their
   GW n run") and check each step is affordable at plausible prices. A path
   that needs a hit must clear the marginal EV threshold per hit — each -4
   judged on its own, never smuggled inside a package.
   - **Start from the model-derived path**, not a blank page:
     `optimize.transfer_path.plan_transfer_path` (printed as the "Transfer path"
     block in the backtest `--propose`) solves the whole horizon at once —
     squad and transfers per gameweek, free transfers accumulating to the
     banking cap, bank carried across periods — and returns THIS week's move,
     the queued forward steps, and `roll_gain`: **what banking the free transfer
     is worth in points**. Quote that number whenever you roll; it is the
     argument the memo owes the reader. Then overlay what it cannot see (it
     freezes prices and minutes, ignores chips, and never re-buys inside the
     horizon) — its forward steps are a candidate plan, not a commitment.
   The plan is a PERSISTENT artifact (`plan.md` beside the decision memos),
   updated every week: current path, target GWs, funds and FT budget each
   step needs. Any proposed transfer — especially a hit — is checked against
   it BEFORE the EV question: a this-week gain that burns the bank or FT a
   planned move depends on is a net loss even when the gate passes it.
   Breaking the plan is allowed only with new information and a written
   reason; drifting out of it silently is not.

4. Feed the manager overlay (models propose, we dispose):
   - `lock` players whose run is about to turn good (refuse the algorithm's
     sale one week before payoff).
   - `ban` buys whose run turns bad inside the horizon when the optimizer is
     chasing one juicy fixture.
   - Record every lock/ban with the fixture-run reasoning in the decision
     memo — an override without written reasoning does not happen.

5. Chip synergy: flag any 3+ GW stretch where multiple owned clubs' runs
   peak together (bench boost window) or a single club's run peaks (triple
   captain) and hand those windows to `/fpl-chip-strategy`.

Output: a "Fixture outlook" section in the gameweek decision memo — runs
table, buy-ahead/sell-ahead list with target GWs, and the planned path for
the next 2-3 transfer windows.

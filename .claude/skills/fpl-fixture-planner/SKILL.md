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
     price and ownership move.
   - **Turning bad** (≥3 of next 5 at FDR ≥ 4, or a derby/top-six gauntlet):
     sell-ahead candidates — plan the exit while value is high; never hold a
     fading run out of inertia.
   - **Split runs** (good now, bad soon): fine for XI now, note the exit GW
     in the plan so the sale is scheduled, not improvised.

3. Plan transfer PATHS, not moves: with 1 FT/GW and banking to 5, write the
   2-3 week sequence ("bank this week → double-move into X+Y before their
   GW n run") and check each step is affordable at plausible prices. A path
   that needs a hit must clear the marginal EV threshold per hit — each -4
   judged on its own, never smuggled inside a package.

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

# A4 acceptance: the model-derived transfer path vs the hand-written one

**Date:** 2026-07-26 · **Runner:** `notebooks/a4_followpath_gw17_24.py` ·
**Verdict:** **PASS — promoted from "do not trust" to evidence-backed advisory.**

## The question

The GW17-24 AFCON window was won on a hand-written FT-banking path: +56 of
edge built through the season's lowest-scoring stretch, 439 actual points.
A4 (`optimize/transfer_path.py`) encodes that logic as a multi-period MILP,
but its first GW25 proposal included a `Saliba -> Raya` churn — exactly the
class of swap the manager overlay vetoed all season — so it shipped flagged
"do not turn it on yet: gate it behind a per-move edge floor and re-run
GW17-24 first." This run is that gate.

## The experiment

Starting state **reconstructed from committed artifacts only** (gw16 players
CSV for the squad, the gw01-16 CSV walk for buy costs, the gw16 memo for
bank/FT/totals) and cross-checked against the committed post-GW24
`state.json` before running: 15 players, £0.0m bank, 4 FT, 941 points.

Both runs replay GW17-24 with `follow_path=True` — the planner decides every
transfer. The committed news overlays are applied (both worlds read the same
news; overlays are inputs, not decisions), but **no manager locks, bans,
caps, captain overrides or chips**. Scoring uses the real vaastav actuals,
autosubs included.

| run | actual | transfers | hits | vs hand | vs field avg |
|---|---|---|---|---|---|
| hand-written (committed) | **439** | 8 | 0 | — | **+60** |
| `follow_path`, edge floor ON (0.5/move) | **438** | 10 | 0 | −1 | **+59** |
| `follow_path`, no floor | 432 | 11 | 0 | −7 | +53 |

Per-GW, floored: GW17 Saliba→J.Timber, Mbeumo→Semenyo, Muñoz→O'Reilly (77);
GW18 O'Reilly→Rice, B.Fernandes→Virgil (36); GW19 Calafiori→Keane (64);
GW20 Szoboszlai→Foden (61); GW21 **roll** (57); GW22 **roll** (32);
GW23 Konaté→Mukiele (40); GW24 Virgil→Chalobah, Foden→B.Fernandes (71).

## What it proves

1. **The floor is the fix, and its value is measured, not asserted: +6 over
   the window.** The unfloored planner transferred every single week — zero
   rolls across an 8-GW stretch whose entire lesson was that banking wins.
   The floored planner rolled GW21 and GW22 (the manager rolled GW20 and
   GW21) and finished within a point of the hand path.
2. **The model path now reproduces the manager's window edge on its own**:
   +59 vs the field against the manager's +60, from the identical entry
   state, with zero hits. The AFCON thesis — sell into the exodus, ride
   banked FTs, requeue the returners — emerges from the MILP without being
   told.
3. **It also found the same shapes**: the GW17 triple-reshape on the banked
   FTs, Calafiori out at GW19, B.Fernandes in by GW24.

## What it does NOT prove — read before trusting it further

- **n = 8 gameweeks, one window, −1 is a tie, not a win.** The claim is
  "no longer worse than the overlay it replaces," nothing stronger.
- **Cross-week flips survive the floor.** O'Reilly was bought GW17 and sold
  GW18; Foden bought GW20, sold GW24; Virgil held two weeks. Each move
  individually cleared the floor, but the manager would call some of this
  plan-thrash. The floor gates within-week churn only; plan *stability*
  across re-solves is unmeasured.
- **Projections come from today's code.** Entry state and actuals are
  identical to the committed run, but the model layer has moved since
  (prior-grading fixes, minutes work), so the planner saw slightly different
  numbers than the manager did at the time. Point-in-time data discipline
  held; code-version discipline cannot, retroactively.

## Standing policy after this run

- `follow_path` **stays opt-in** (`--follow-path`, still no default-on
  path). What changes is the posture: the path block in `--propose` is now
  an evidence-backed advisory the memo must ANSWER, not a curiosity.
- The per-move edge floor (`MOVE_EDGE_FLOOR = 0.5` decayed pts, equal to
  `ROLL_DECISIVE_EDGE` so verdict and rationale cannot contradict) is ON by
  default for every path solve, live included.
- The manager overlay retains the veto (CLAUDE.md rule 4). The next
  escalation — letting the path *decide* live transfers — needs a second
  window replayed (GW25+ when scored) plus a plan-stability measure.

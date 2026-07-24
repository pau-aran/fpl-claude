# Chip counterfactual — the AFCON window (GW17-20)

*Phase 3b validation. Non-destructive: our committed FT-only results stand (forward-only
fidelity). Each chip scenario is scored on ACTUALS, but the squads are chosen POINT-IN-TIME
— Free-Hit/Wildcard squads are built from that GW's projections using the same committed
overlays that marked the known-out players; Bench-Boost/Triple-Captain deltas come from the
committed per-player CSVs. Machinery: `src/fpl_claude/backtest/simulate.py` chips + `--chip`.*

## TL;DR — not chipping the AFCON window was correct; the only value chip was Bench Boost

| GW | our FT-only | Free Hit (pit) | FH Δ | Bench Boost | BB Δ | Triple Capt Δ |
|----|------------|----------------|------|-------------|------|----------------|
| 17 | 70 | 76 | **+6** | 81 | **+11** | **+16** |
| 18 | 43 | 39 | −4 | 55 | +12 | +2 |
| 19 | 62 | 44 | −18 | 81 | **+19** | +2 |
| 20 | 63 | 53 | −10 | 68 | +5 | +2 |

- **Wildcard @ GW17, then held 4 GWs: 236 vs our 238 (−2).** A point-in-time WC build on GW17
  projections bought Calafiori and B.Fernandes (both fine at GW17) — who then got injured
  GW18-20 — plus Gakpo/Dewsbury-Hall/Keane/Mukiele. Locked in, it could not react to the
  rolling injuries our FREE transfers handled (Bruno→Semenyo GW18, Calafiori→Timber GW19).
  **The Wildcard actively lost points here** because the window's value was reactivity, not a
  one-shot reshape — and our squad only needed 2 changes, far inside the FT budget.
- **Free Hit never helped** (only +6 at GW17; −4/−18/−10 otherwise). Our squad was already
  strong and the weeks were low-scoring league-wide, so a one-week FH team beat our own only
  marginally, once. FT-only was the right call.
- **Bench Boost was positive every week** (+11/+12/+19/+5) — it would have captured exactly
  the "stranded bench" hauls the GW17-20 reviews flagged as variance (GW17 Saliba 6; GW19
  Brooks 10 + Konaté 7; GW18 Dúbravka 11 was a GK, so not fully BB-capturable behind Roefs).
- **Triple Captain's one big week was GW17** (Haaland 16 → tripled, +16); GW18-20 it was worth
  only +2 because the captain blanked 2/2/2.

## What this means (process, not hindsight)

1. **The disciplined FT-only ride through the AFCON window was right.** The two reshaping chips
   (WC, FH) were negative-to-neutral; a Wildcard would have *cost* us ~2 pts. Chips that rebuild
   the squad are wasted when you only need a couple of reactive changes — which is exactly the
   AFCON+injury pattern we hit, and FTs covered it for free.
2. **Bench Boost is the window's value chip — but the GW19 +19 was largely bench VARIANCE, not a
   pre-hoc signal.** Ex-ante our GW19 bench held a known-out Rice and a bench keeper; the +19
   came from a rotation-fringe (Brooks 10) and a benched CB (Konaté 7) over-scoring. So BB was
   not a clear pre-deadline call any week here (a strong BB week needs 4 nailed, well-fixtured
   bench starters — we never had that in the window). Honest read: BB was the best chip
   *ex-post*, but not an obvious *ex-ante* one. Logged for the live pipeline: only fire BB when
   all four bench slots are nailed starters with green fixtures (typically a DGW).
3. **Triple Captain @ GW17 (+16) was the most defensible ex-ante chip** — Haaland, top
   projection, ~90% EO, soft home fixture. We did not model chips at the time; going forward TC
   is the cleanest chip to deploy on a premium captain's standout single fixture (or a DGW).

## Forward use (GW21-24 and live 2026/27)

- **Hold WC/FH** — no trigger in a squad that stays largely intact on FTs. The real WC/FH
  trigger is a genuine 4+ change need or a Blank/Double GW (the chip planner's `/fpl-chip-strategy`
  DGW/BGW detection). AFCON alone, ridden on banked FTs, is not it (this analysis proves it).
- **Triple Captain** — reserve for a premium captain's standout fixture or a DGW; GW17-type
  soft-home-Haaland weeks are the pattern.
- **Bench Boost** — reserve for a DGW where all 15 have two fixtures; do NOT fire on a single
  GW hoping for bench variance.
- The two-sets-per-half inventory (WC/FH/BB/TC each half; set 2 unlocks GW20) is now tracked in
  `state.json:chips_used` and enforced one-per-half by the simulator.

*Reproduce: the scenarios were generated with the new chip machinery (score_gw chip=…,
wildcard_squad, run_gameweek chip branches). Live/forward runs pass `--chip <name>` or the
decision-JSON `"chip"` field.*

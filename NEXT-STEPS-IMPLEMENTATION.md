# Next Steps — fixes & implementation backlog

*Created 2026-07-24 after the GW18-20 simulation + Phase 3b chip mechanics. Companion to
`NEXT-STEPS.md` (the road-to-GW1 roadmap) and `STATE.md` (session handoff). This file is the
prioritized "what to build/fix next" list, split by whether it's buildable now or gated on an
external factor. Tick items off and move them to `NEXT-STEPS.md`/`STATE.md` as they land.*

## Just shipped (this session)
- **GW18-20 backtest** (AFCON+festive trough): +42, season 1179, edge +177. Reviews, memos,
  overlays, consensus, plan/knowledge updates committed.
- **Phase 3b chip MECHANICS** in the backtest simulator: `wildcard`/`free_hit`/`bench_boost`/
  `triple_captain` playable via `decision.chip` or `--chip`; `score_gw` (BB all-15, TC ×3),
  `run_gameweek` (WC keep / FH revert), inventory tracked one-per-half in `state.json`,
  `canonical_chip` alias/validation. 6 new tests (`tests/test_chips.py`), 46 green.
- **AFCON chip counterfactual** (`reports/backtest/2025-26/chip-analysis-afcon.md`): proved
  FT-only was right (WC −2, FH neutral/negative, BB gains were variance, TC@17 +16).

## A. Buildable NOW (no network / no season-launch dependency)

### A1. Chip follow-ups (finish Phase 3b)
- [x] **Automatic chip-TIMING in the decision layer.** (shipped: `optimize/chip_timing.py` —
      `chip_surface` scores every future `xpts_gw{n}` for TC-best-captain / BB-bench-sum with
      minutes-nailedness, `advise` gives per-chip advise/hold + target GW; wired into
      `/fpl-chip-strategy` step 3.)
- [x] **DGW/BGW detection** from fixture-diff monitoring (the real WC/FH/BB trigger). (shipped:
      `chip_timing.detect_double_blank` — per-GW fixtures-per-team counts → DGW (≥2) / BGW (0)
      team sets; feeds the WC/FH/BB gates, single-GW punts stay noise.)
- [x] **Encode the chip timing rules** (knowledge.md): TC on a standout captain fixture/DGW;
      BB only when all 15 are nailed with fixtures; WC/FH only for a 4+ change need or BGW/DGW.
      (shipped: already in the knowledge.md chips entry; now in CODE as `advise()` gates +
      explicit threshold constants — `TC_STANDOUT_XPTS`, `BB_MIN_EXTRA_EV`, `NAILED_MIN_MINUTES`,
      `SQUAD_DGW_MIN_DOUBLERS`, `WC_CHANGE_THRESHOLD`, one-per-half via `HALF_BOUNDARY_GW`.)
- [x] **`--propose` should surface a chip suggestion** (e.g. "BB not advised: 2 bench slots
      are non-nailed") so the deadline run considers chips explicitly. (shipped: `run.propose`
      prints a "Chip advice" block — current-half verdicts + a forward EV surface, inventory-aware
      via `state.chips_used`.)

### A2. The one open MODELING defect — level/captain calibration  ✅ RESOLVED (Path A)
- [x] **Resolved the knowledge.md ⇄ NEXT-STEPS inconsistency** — both now read `[DONE/process]`.
      The 20-GW decomposition (`reports/backtest/2025-26/calibration.md`) also corrected the
      framing: the mean under-prediction lives in the BASE XI (+4.3/GW, within noise t=1.47),
      NOT the doubled captain, which is mean-UNBIASED (−0.07) and only high-variance.
- [x] **Formally closed as "ranking-correct, EV-reporting-only, no model change"** — the
      captain-slot / bonus build was rejected on the numbers (uniform calibration is a proven
      no-op on picks + the hit-gate; "scale to league level" inoperable, corr +0.06). Captain
      slot now logged separately in the REPORTING code path (`predicted_xi_breakdown` in
      `simulate.py`; `write_memo` Outcome line; +1 test), not just the review skill. The one
      residual signal (starting MIDs +1.2, bonus proxy) left `[WATCH]` for Minutes-v2.

### A3. Live `/fpl-review` calibration loop
- [ ] Wire `/fpl-review` to consume `db/projections/` CSVs (predicted) vs FPL actuals and
      emit the calibration log automatically (today it's a manual backtest artifact).

### A4. Multi-period transfer path in the MILP (Phase 3b other half)
- [ ] The "bank FTs toward the returnee window" logic is currently a hand-written `plan.md`
      overlay. Make the multi-week path native to the optimizer (rolling FT value, planned
      2-3 week moves) so the standing plan is model-derived.

### A5. Data-source clients (code now; live-test when networked)
- [ ] **Understat** xG/xA client (post-2025-API-change) → feed `models/rates.py`.
- [ ] **FPL-Core-Insights** puller (match stats + Club Elo, FPL-ID-keyed).
- [ ] **ID mapping** FPL ↔ Understat ↔ FBref (seed from FPL-Core-Insights).
- [ ] **Odds blend** into the team model (Phase 2b): blend market CS/goals into Dixon-Coles.

### A6. Minutes v2
- [ ] LightGBM on vaastav history with congestion / Euro-week / AFCON features (the current
      minutes model is a v1 heuristic — our single biggest edge, worth the upgrade).

### A7. Weekly flagship report — never dry-run
- [ ] `reports/weekly/` is empty; `team_week.py` has produced zero output. Do a dry-run
      (websearch-driven multi-competition results + the vaastav data) to validate the builder
      before GW1, since it's a first-class deliverable.

### A8. Continue the backtest (optional, high-signal) — DONE ✅
- [x] Simulated GW21-24 to close the AFCON window (season **1380, +191** vs baseline; window
      GW17-24 net **+56** of edge; 1 hit all season, captaincy 24/24). The returnee decisions
      landed on the numbers: GW21 rolled to the FT cap (+13); GW22 the Semenyo £64m-clause
      risk-class sale → Bruno G. over the solver's Foden (−2, both refusals vindicated same
      week); GW23 REFUSED the £14 Salah buy-back on written arithmetic + held through a
      bereavement (−6, priced-variance week); GW24 entered **B.Fernandes over Mbeumo** on
      horizon/value-per-£m (+9, right by +8 vs the deferred Mbeumo). Exercised the new chip-EV
      surface every week (chip advice printed in `--propose`; TC@GW26 DGW candidate surfaced
      and confirmed via news) and the calibration split (base-XI vs captain-slot Outcome line).
      Two NEW process rules shipped from the run: (a) list + explicitly call every <0.2-hair
      bench margin (GW22 Tarkowski sting), (b) the pure-CS duel-name CAUTION (0-for-2). One
      [WATCH] opened: widen the DEF-CS bench hair to ~0.3 (Konaté GW24 + Tarkowski GW22, two
      bimodal-CS bench stings). Memos/reviews/consensus/overlays all committed GW21-24.

## B. BLOCKED / time-gated (cannot do in this sandbox / before the game opens)
- [ ] **First live 2026/27 data run** — FPL API + football-data egress-blocked here; needs a
      networked session (GitHub + WebSearch work; vaastav self-provisions).
- [ ] **Season-launch rules verification** — `2026-27.yaml` is `verified_against_official:
      false` with chip counts literally `"unverified"`. Reconcile vs the official site when the
      2026/27 game opens (~mid-August); set `verified_against_official: true`. The live
      optimizer refuses to run until this is done.
- [ ] **Automation arming** (Phase 5) — scheduled sessions (daily refresh/news, Monday team
      reports, T-48h/24h/2h deadline runs, post-GW review). Depends on the two above.
- [ ] **GW1 2026/27 draft squad** (Phase 4) — depends on live data + verified rules.

## Suggested order
1. ~~A2 (close the calibration defect)~~ — **DONE** (Path A, `calibration.md`; memo split shipped).
2. ~~A1 (chip timing + DGW/BGW detection)~~ — **DONE** (`optimize/chip_timing.py`, `--propose`
   advice, exercised live GW21-24; TC@GW26 DGW surfaced).
3. ~~A8 (GW21-24 backtest)~~ — **DONE** (window closed at +191; two new process rules + one
   [WATCH] shipped from the run).
4. **A4/A3 next** (multi-period MILP transfer path + live `/fpl-review` calibration loop) —
   now the highest-leverage remaining buildable items; A4 would make the hand-written `plan.md`
   FT-banking/returnee-window path model-derived (the GW17-24 window proved the manual version
   works, +56 edge — worth encoding).
5. A5/A6/A7 (data breadth, minutes v2, weekly-report dry-run) as capacity allows.
6. B items the moment a networked session / the 2026/27 season opens.

## Backtest reach (as of this session)
- **24 of 38 GWs simulated** point-in-time: season **1380 vs baseline 1189 (+191)**, 1 hit
  all season, captaincy 24/24. AFCON window (GW17-24) net **+56**. The pipeline now has chip
  MECHANICS + TIMING advisory, the calibration defect closed, and two bench-order process
  rules. Next backtest frontier (optional): GW25-26 to exercise the FIRST live chip play
  (TC@GW26, Arsenal DGW) and GW31 (BGW, a Free Hit/WC trigger) — the chip surface is built and
  waiting for a DGW/BGW to actually fire a chip in-sim.

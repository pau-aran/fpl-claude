# Next Steps — fixes & implementation backlog

*Created 2026-07-24 after the GW18-20 simulation + Phase 3b chip mechanics. Companion to
`NEXT-STEPS.md` (the road-to-GW1 roadmap) and `STATE.md` (session handoff). This file is the
prioritized "what to build/fix next" list, split by whether it's buildable now or gated on an
external factor. Tick items off and move them to `NEXT-STEPS.md`/`STATE.md` as they land.*

## Just shipped (2026-07-25 session — A3 + A4, the last two buildable frontier items)
- **A3 — live `/fpl-review` calibration loop** (`src/fpl_claude/reports/calibration.py`, log at
  `notebooks/calibration.md`, 24 tests). Point-in-time enforced: a snapshot dated after the
  deadline is REFUSED, not silently used, and every rejection is named in the log entry.
  Verified against the real archive — it reproduces the GW24 memo Outcome line exactly
  (53.68 = base XI 40.96 + captain slot 12.72).
- **A4 — multi-period transfer path native to the MILP** (`optimize/transfer_path.py`, 12 tests).
  A genuine multi-period solve (own/xi/buy/sell per player per GW, integer FT banking to the
  rules cap, cumulative bank), surfaced as a "Transfer path" block in `--propose`. **Advisory
  only:** `decide_transfers(follow_path=True)` is opt-in, default off, not on the CLI — so every
  committed backtest result is byte-identical.
- **Windows console fix** (`src/fpl_claude/console.py`): every CLI reconfigures stdout to UTF-8.
  Found by running A3's CLI for real — it computed the whole calibration and then died on
  `UnicodeEncodeError` printing `−`/`≥` under cp1252. `run.py` was the same shape: a GW25
  proposal prints `Petrović` (U+0107, absent from cp1252), so player names alone would abort it.
- **`docs/environment.md`**: the local workstation is **not** egress-blocked — FPL API,
  football-data and Understat all return 200. That constraint was always the cloud sandbox's,
  not the project's, so NEXT-STEPS §1 (first live data run) is runnable from the owner's machine.

## Previously shipped (2026-07-24 session)
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

### A3. Live `/fpl-review` calibration loop — DONE ✅
- [x] Wire `/fpl-review` to consume `db/projections/` CSVs (predicted) vs FPL actuals and emit
      the calibration log automatically. (shipped: `reports/calibration.py` +
      `python -m fpl_claude.reports.calibration --gw N`; skill step 5 now runs the command.
      Metrics overall / per position / base-XI vs captain-slot, `ep_next` carried as a
      side-by-side benchmark, owned-squad and whole-pool cuts separated, append-only log.)
- [ ] **Follow-up:** the live FPL-API actuals path (`--actuals live`) is UNVERIFIED end to end —
      it was only exercised through an injected payload. Confirm it against a real
      `event/{gw}/live` before trusting a live-week entry.
- [ ] **Follow-up:** `--squad` is a manual input for live weeks (no committed live squad state
      exists yet); without it you get pool metrics only. A `--since` multi-GW trend roll-up over
      the log is the natural next step.

### A4. Multi-period transfer path in the MILP (Phase 3b other half) — DONE ✅ (advisory)
- [x] The "bank FTs toward the returnee window" logic is no longer only a hand-written `plan.md`
      overlay. (shipped: `optimize/transfer_path.py` — a genuine multi-period MILP with
      own/xi/buy/sell per (player, GW), integer FT banking to the rules cap, cumulative bank so a
      GW+1 sale funds a GW+2 buy, and a roll-vs-move price on banking. Wired into `--propose` as
      a "Transfer path" block; ~9s for a 5-GW solve over a 70-player pruned pool.)
- [ ] **NOT yet trusted to decide.** `decide_transfers(follow_path=True)` is opt-in and default
      OFF, with no CLI flag, so committed backtest results are unchanged. Before turning it on:
      its GW25 proposal was a three-move reshape including a `Saliba → Raya` churn — precisely
      the class the manager overlay has vetoed all season (the "7th churn veto", GW11). It has
      ZERO points-scored evidence: no backtest has been re-simulated with `follow_path=True`.
      Consider a per-move minimum-edge floor and/or a lower `MAX_MOVES_PER_GW` first, then
      re-run GW17-24 with it on and compare against the +56 the hand-written path actually made.

### A5. Data-source clients (code now; live-test when networked)
- [ ] **Understat** xG/xA client (post-2025-API-change) → feed `models/rates.py`.
- [ ] **FPL-Core-Insights** puller (match stats + Club Elo, FPL-ID-keyed).
- [ ] **ID mapping** FPL ↔ Understat ↔ FBref (seed from FPL-Core-Insights).
- [ ] **Odds blend** into the team model (Phase 2b): blend market CS/goals into Dixon-Coles.

### A6. Minutes v2 — DONE ✅
- [x] **LightGBM minutes model shipped** (`models/minutes_v2.py` + `notebooks/minutes_v2_eval.py`,
      artifact gitignored under `db/models/`, retrainable with a fixed seed). Four heads
      (p_start / p_play / p60 / minutes-given-start) on vaastav 2022-23→2024-25, holdout 2025-26,
      with congestion (rest days, fixtures in prior 7/14d), midweek/Euro-week, AFCON-window and
      post-international-break features. Wired in behind a `ModelMinutes` hook: no lightgbm or no
      artifact → byte-identical v1 output, and the news **overlay still overrides everything**.
      Cold starts are declined by design (no history → v1 prior path), which is the honest answer.
      **Holdout vs v1:** p_start log loss 0.454→0.246, p60 0.386→0.252, expected-minutes MAE
      18.75→12.40 (bias 0.80→0.06), within-GW bench-order AUC 0.903→0.946. Wins on every slice
      that matters — post-international-break 0.600→0.269, long rest 0.506→0.264, the
      rotation-prone 0.3-0.8 band 0.755→0.530, AFCON window 0.453→0.246. Numbers in
      `reports/models/minutes-v2.md` + `minutes-v2-metrics.json`; 38 new tests incl. a no-leakage
      property and overlay-precedence.

### A7. Weekly flagship report — dry-run DONE ✅ (enrichment partial)
- [x] **Builder validated end-to-end against LIVE 2026/27 data** and fixed: UTF-8 writes (Windows
      cp1252 was mangling accented names), point-in-time week directory from the snapshot date
      instead of `date.today()`, pre-season/empty-window handling (opening-run view instead of 20
      files of "no matches"), the price/ownership movers section the docstring promised but never
      implemented (degrades cleanly with no prior snapshot), `--out-dir` CLI. First real output
      committed: `reports/weekly/2026-30/` — all 20 clubs + a real `index.md` (GW1 fixture, opening-5
      FDR, flags, movers). New offline `tests/test_team_week.py`. Skill updated with what the
      dry-run proved.
- [ ] **Enrichment is 8/20** (Arsenal, Aston Villa, Bournemouth, Chelsea, Coventry, Crystal Palace,
      Everton, Fulham carry sourced pre-season notes; the other 12 are builder skeletons). Finish
      the remaining 12 on the next `/fpl-team-week-report` run — the format is proven.

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

## B. BLOCKED / time-gated (before the game opens — the *network* half is now UNBLOCKED)
- [x] **First live 2026/27 data run — NO LONGER NETWORK-BLOCKED.** Tested 2026-07-25 from the
      owner's Windows machine: `fantasy.premierleague.com`, `www.football-data.co.uk` and
      `understat.com` all return 200 (`docs/environment.md`). The 403s were the cloud sandbox's
      egress policy, never the project's. Still gated on the season actually opening — the
      2026/27 bootstrap has no meaningful data until then — but it can be run from here.
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
4. ~~A4/A3 (multi-period MILP transfer path + live `/fpl-review` calibration loop)~~ — **DONE**
   (`optimize/transfer_path.py`, `reports/calibration.py`; 103 tests green). Both shipped
   ADVISORY: the path does not decide transfers yet and the live actuals path is unverified.
5. **Next: prove A4 before trusting it** — add a per-move minimum-edge floor, then re-simulate
   GW17-24 with `follow_path=True` and compare against the +56 the hand-written path made. A
   model-derived path that churns is worse than the overlay it replaces.
6. ~~A6/A7 (minutes v2, weekly-report dry-run)~~ — **DONE** (parallel agents);
   A5 (data breadth) remains, and it is now unblocked — see below.
7. **B items are LIVE NOW.** This session reached both `raw.githubusercontent.com` **and**
   `fantasy.premierleague.com/api` (HTTP 200), and the **2026/27 game is OPEN**: 20 teams
   (COV/HUL/IPS promoted), 558 elements, 38 events, **GW1 deadline 2026-08-21 17:30 UTC**.
   That unblocks the first live data run, the `2026-27.yaml` rules verification (the live
   optimizer refuses to run until `verified_against_official: true`), and the GW1 draft squad.
   The bootstrap advertises 8 chips (2× wildcard, 2× freehit, 2× bboost, 2× 3xc) — reconcile
   against the official rules page before trusting it.

## Backtest reach (as of this session)
- **24 of 38 GWs simulated** point-in-time: season **1380 vs baseline 1189 (+191)**, 1 hit
  all season, captaincy 24/24. AFCON window (GW17-24) net **+56**. The pipeline now has chip
  MECHANICS + TIMING advisory, the calibration defect closed, and two bench-order process
  rules. Next backtest frontier (optional): GW25-26 to exercise the FIRST live chip play
  (TC@GW26, Arsenal DGW) and GW31 (BGW, a Free Hit/WC trigger) — the chip surface is built and
  waiting for a DGW/BGW to actually fire a chip in-sim.

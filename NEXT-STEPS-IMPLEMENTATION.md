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
- [ ] **Automatic chip-TIMING in the decision layer.** Mechanics exist; the optimizer still
      can't *choose* when to chip. Add a chip-EV surface: for each future GW, evaluate
      TC-best-captain, BB-if-all-15-play, and flag DGW/BGW candidates. Wire into
      `/fpl-chip-strategy` so the season chip calendar is model-driven, not hand-run.
- [ ] **DGW/BGW detection** from fixture-diff monitoring (the real WC/FH/BB trigger). The
      counterfactual showed single-GW chip punts are noise; the value is in doubles/blanks.
- [ ] **Encode the chip timing rules** (knowledge.md): TC on a standout captain fixture/DGW;
      BB only when all 15 are nailed with fixtures; WC/FH only for a 4+ change need or BGW/DGW.
- [ ] **`--propose` should surface a chip suggestion** (e.g. "BB not advised: 2 bench slots
      are non-nailed") so the deadline run considers chips explicitly.

### A2. The one open MODELING defect — level/captain calibration
- [ ] **Resolve the knowledge.md ⇄ NEXT-STEPS inconsistency**: knowledge.md still lists level
      calibration `[OPEN]` with an unbuilt "environment-level calibration term"; NEXT-STEPS
      §2 calls it `[DONE/process]`. Pick one. 20-GW mean error is ~+4.0, concentrated in the
      doubled-captain slot (Haaland 2/2/2 across GW18-20).
- [ ] **Build the captain-ceiling / bonus-signal improvement** OR formally close it as
      "ranking-correct, EV-reporting-only, no model change" with the captain slot logged
      separately. This is the last standing modeling gap before GW1.

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

### A8. Continue the backtest (optional, high-signal)
- [ ] Simulate GW21-24 to close the AFCON window on the pipeline — the returnee decisions
      (Mbeumo/Bruno ~GW22, Salah ~GW23), the Liverpool ARS(A)5 reassess (GW21), and a first
      live chip-EV check (set 2 unlocks GW20). Watch the `force_start` duel-lever rule.

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
1. A2 (close the calibration defect — last modeling gap before GW1).
2. A1 (finish chip timing + DGW/BGW detection — the biggest untapped rank lever).
3. A8 (GW21-24 backtest — exercises A1/A2 and the returnee logic end-to-end).
4. A4/A3 (multi-period path + live calibration loop).
5. A5/A6/A7 (data breadth, minutes v2, weekly-report dry-run) as capacity allows.
6. B items the moment a networked session / the 2026/27 season opens.

# Backtest 2025/26 GW1–10 — evolution log

*One entry per gameweek, appended by the weekly review loop. Each entry
separates process from variance (CLAUDE.md rule 3) and records the pipeline
improvements the week's evidence justified — improvements apply from the NEXT
gameweek onward; past results are never rerun.*

## Pre-season engineering (found while building the harness, before GW1)

- **Rates explosion on tiny samples** — 1 minute + 0.06 xG projected as a
  5.4 xG/90 captain pick (Mheuka). Fix: pseudo-minute shrinkage in
  `models/rates.py` (`SHRINKAGE_MINUTES = 90`). Applies to the live pipeline.
- **Dixon-Coles trusted 1-match teams** — promoted Sunderland's opening 3-0
  produced a rating that captained their £4.6m defender with +50 "EV". Fix:
  `MIN_TEAM_MATCHES = 5` coverage floor in `models/team.py`, FDR fallback
  below it. Applies to the live pipeline (matters every promoted-team season).
- **End-of-season files leak January transfers** — vaastav `players_raw.csv`
  team/position are final-state; point-in-time values must come from
  `merged_gw` rows at-or-before the GW. Backtest-only, but a warning for any
  future historical training data (Minutes v2).

---

## GW1 review

### 1. Score summary — predicted 55.31, actual 84 (+28.69)

Decomposition of the +28.69 XI gap (actual − predicted, per player):

- **Variance, positive (~+29):** Semenyo +11.7 (2 goals off 0.91 xG) and
  Wood +8.8 (2 goals off 0.95 xG) are finishing over-performance on picks the
  model priced correctly at the underlying level — right process, lucky
  outcome. Raya +5.8 (7 saves, 3 bonus) is save-volume/bonus variance.
- **Process-attributable, positive (+4):** Saliba +2 and Aït-Nouri +2 in
  defensive-contribution points the model structurally could not predict
  (see proposal below). This is a model gap, not luck.
- **Process-attributable, negative (−4.07):** Gvardiol projected 4.07,
  played 0 (see process check).
- **Captain:** Salah predicted 15.78 doubled, actual 16. Essentially exact.

### 2. Process check

- **Captain call: PASS.** Salah was the highest-projection player in the
  squad (7.89) at home to Bournemouth; he returned goal+assist-level output
  (8, ×2 = 16). Haaland (13) out-scored him but was not in the squad —
  a defensible one-premium build choice, not a captaincy error.
- **Gvardiol 0 minutes: mostly variance, with one process ding.** No FPL
  flag or public pre-deadline news signalled a benching; City's XI vs
  Wolves (Aït-Nouri, Dias, Stones, Lewis) was classic Pep rotation,
  unknowable in the specific. The process failure is category-level: we
  fielded TWO £6.0m City defenders with no written rotation-risk overlay,
  in the first post-Club-World-Cup season — doubling exposure to a known
  rotation regime without pricing it. One of the two was always at risk.
- **Justin 0 minutes (bench): variance-adjacent, low cost.** He has no GW1
  row in merged_gw at all (not in the matchday squad); no pre-deadline flag
  in the data we replayed. Cost nothing directly — but see bench note.
- **Bench construction: FLAG.** All three outfield bench players logged 0
  minutes (Justin, Mheuka, Scarlett), so Gvardiol's 0 could not autosub.
  The model itself said so (Mheuka 1.19, Scarlett 1.16 predicted ≈
  no-minutes fodder). £4.0m *playing* enablers existed (Gudmundsson 4.0m
  scored 9; Acheampong 4.0m scored 9 — findable via minutes, not hindsight).
  Watch: does the optimizer value bench p_play at all? Candidate for a
  future GW's improvement; not this week's pick.
- **Overlay quality: PASS.** The one hand-written overlay (Dúbravka
  start_share=0.85, with sources) was correct — he started and played 90.
- **Misses in the actuals: mostly unknowable.** Top league scores were
  Ballard 17 (promoted-team DEF: goal + DC — below our MIN_TEAM_MATCHES
  coverage floor, correctly untrusted pre-GW1), Richarlison 13 (2 goals off
  0.78 xG), Calafiori 13, Ekitiké 11 (new signing, no prior, low_sample —
  honestly flagged soft). We already owned two of the top six scorers
  (Semenyo 15, Wood 13). The only *projectable* class of missed points was
  defensive contribution — the systematic item below.

### 3. Calibration note

Predicted 55.31 vs actual 84 reads as badly low, but one GW proves nothing:
~+25 of the gap is finishing/saves/bonus variance that mean-reverts. Two
components ARE systematically low and worth watching over GW2–4:
(a) defensive contribution is projected at exactly 0 for everyone (structural,
fixed below — in GW1 reality, 15/100 playing DEFs and 10 MID/FWDs banked +2);
(b) the bonus90 prior-proxy looks light (our XI took 12 actual bonus pts).
Do not touch the level until 3–4 GWs of predicted-vs-actual are logged;
log the per-component bias each week.

### 4. Improvement proposal (the one change): stop shrinking dc90 toward a phantom-zero prior

- **File:** `src/fpl_claude/models/rates.py`, function `blend()`.
- **Bug mechanism:** `defensive_contribution` is new for 2025/26; the
  2024/25 prior bootstrap has no such field, so `from_bootstrap` yields
  dc90 = 0 for every prior row. `blend()` then treats that 0 as *evidence*
  and shrinks current-season dc90 toward it with weight
  `1 − min(1, minutes/540)` — so even after real GW1 DC data exists (e.g.
  Aït-Nouri 15 CBIT+tackles in one match), the projection suppresses it by
  ~83%, and full weight isn't reached until ~6 matches. Every DEF/MID
  DC projection is materially biased low for the first third of the run-in.
- **Fix:** in `blend()`, per rate column, treat an all-zero prior column as
  "stat did not exist in the prior season" and exclude that column from
  prior-shrinkage — the current-season rate (already damped by
  `SHRINKAGE_MINUTES` pseudo-minutes in `_per90`, so no small-sample
  explosion) stands on its own. Roughly:
  `cols_to_blend = [c for c in RATE_COLUMNS if merged[f"{c}_prior"].abs().sum() > 0]`.
  General (covers any future new stat), ~3 lines, unit-testable: prior with
  all-zero dc90 ⇒ blended dc90 == current dc90; prior with nonzero dc90 ⇒
  behavior unchanged.
- **Why GW1 justifies it:** 25 players earned +2 DC in GW1 while the model
  predicted 0.0 DC points for all 692 rows; our own squad leaked +4
  unpredicted (Saliba 14 CBIT+tackles, Aït-Nouri 15) and Szoboszlai missed
  the MID threshold by 1 (11 vs 12) — that near-miss is exactly the kind of
  probability mass `poisson_sf` in `xpts.py` is built to price and currently
  can't, because its dc90 input is strangled at the source. DC re-ranks the
  whole cheap-defender value board (Moneyball rule 1), so this compounds
  into every future transfer and XI call. No future data involved: from GW2
  onward the fix only lets *already-played* GWs' DC evidence through.
- **Applies from GW2 onward; GW1 is not rerun.**

---

## GW2 review

### 1. Score summary — predicted 59.01, actual 44 (net of -4 hit; XI raw 48, gap −11.01)

Per-player XI gap (actual − predicted, captain doubled), grouped:

- **Variance, negative (−12.9):** Palmer −5.52 — 0 minutes with NO pre-deadline
  flag or news; withdrawn injured after the 22 Aug deadline (groin, warm-up).
  Unknowable; not a selection error. Salah(C) −4.22 — 10 vs 14.2 doubled; he
  played 90 and returned, ordinary attacking variance. Aït-Nouri −3.37 — hooked
  after 22 minutes, unflagged.
- **Process-attributable, negative (−3.10):** Ballard, bought this week,
  predicted 4.10, benched (8 min). The minutes model gave him
  p_start=1.0 with confidence "season" off ONE start: `_start_share` in
  `models/minutes.py` trusts `starts/team_games` for any team_games>0 when no
  prior exists (promoted team ⇒ no prior). One GW of team sheets became
  certainty. Same family of error as the ev_delta finding below.
- **Positive tail (+9.1):** Ekitiké +3.3 (9 pts, goal again), Saliba/Muñoz/
  Raya/Semenyo +1.3–1.6 each — small over-delivery, partly the DC-adjacent
  defensive floor.
- 44 vs official average 51: first below-average week. Season 128 vs
  average-manager baseline 105 (54+51): **+23**.
- **GW1 DC fix check:** behaved as designed, no squad player crossed a DC
  threshold in GW2 (Szoboszlai closest, 9 CBIRT vs 12; league-wide 18 DEF +
  9 MID/FWD did). But note it has a noise cost early: Ballard's dc90=7.0 comes
  from one 14-CBIT match (halved only by pseudo-minutes), and that DC mass is
  part of what made him the model's top ≤£4.6m pick. Watch, don't revert.

### 2. The hit — Wood → Ekitiké for -4: **process FAIL (outcome fine)**

Reproduced the deadline solve exactly (objective 281.43 vs roll 265.98,
ev_delta +15.447 — matches the memo). Decomposition by re-solving at
max_transfers 0/1/2:

- **Free leg (Gvardiol → Ballard): +12.97** of the +15.45. Gvardiol was ruled
  out in Pep's 22 Aug presser (overlay start_share=0) — a correct, essentially
  forced free move. But the overlay zeroes him for the ENTIRE 8-GW horizon
  (projections apply one minutes estimate to every horizon GW), so his
  xpts_horizon collapsed to 1.94. A knock that costs ~1–2 GWs was priced as an
  8-GW absence; the true delta of this leg is roughly +4, not +18.35 vs
  Ballard's 20.29. Most of the quoted +15.45 was this phantom.
- **Hit leg (Wood → Ekitiké): +2.48 marginal**, net of the -4 (gross +6.48;
  Ekitiké xpts_horizon 27.60 vs Wood 21.21, gap 6.39). **+2.48 < the 4.5
  threshold** — the hit fails our own policy when judged on its own merits. It
  passed because `decide_transfers` (backtest/simulate.py) tests the PACKAGE
  ev_delta (15.45) against the threshold, so the free leg's inflated EV
  smuggled the hit through. That is a policy-gate miswire, not a projection
  judgment call.
- **Is the Ekitiké−Wood gap itself trustworthy?** No. Ekitiké's xg90=0.637 is
  built on 1.14 xG in 71 minutes — one match — kept unshrunk because a new
  signing has no prior; `blend()` flags him `low_sample=True` and nothing
  downstream consumes the flag. Wood, meanwhile, is shrunk 86% toward his
  20-goal 2024/25 prior (blended xg90 0.41 despite 0.95 xG in GW1). The model
  structurally prefers the 1-match hot streak of a newcomer over an
  established talisman — early-season projection noise treated as
  horizon-stable truth, exactly as suspected. The claimed ~15 was never
  "Ekitiké over Wood"; even the real 6.39 is soft.
- **Deadline-information verdict:** selling a nailed 13-pt talisman one GW
  into the season, on a hit, for a 1-match sample, was not justified. Ekitiké
  9 vs Wood 2 (net +3 after the hit) is variance repaying a bad process —
  record it as such (rule 3).
- **Is hit_ev_threshold=4.5 too permissive?** The number wasn't the failure —
  the gate never saw the hit's marginal EV at all. Keep 4.5 (net of hit cost)
  but apply it marginally (see §5); revisit the level once the calibration log
  has ~6 GWs. A projection-confidence haircut (shrink low_sample horizons) is
  the complementary fix, queued behind §5.

### 3. Captaincy, bench, autosubs

- **Captain: PASS.** Salah was the squad's (and league's) top projection
  (7.11 > Haaland 6.52) at Newcastle; returned 5 (Haaland managed 2).
  Right call ex ante and ex post.
- **Vice: PASS mechanically** (Ekitiké, 2nd-highest XI projection); not needed.
- **Bench: zero coverage AGAIN.** Second straight GW all three outfield bench
  players logged 0 minutes (Justin — second week not in the squad, availability
  proxy already at 0.3, drops to 0.12 for GW3; Scarlett; Mheuka). Palmer's
  post-deadline 0 could not autosub. This week the flag from GW1 gets a
  counter-note: the best PLAYING ≤£4.6m enabler by the model's own numbers
  (Gudmundsson, xpts 3.64) actually scored **−1** in GW2, so coverage would
  have cost a point here. EV of playable bench is still positive; urgency
  reduced, still queued behind §5.
- **Autosubs: none fired** (correctly — no bench player had minutes).
  Dúbravka's 6 pts stayed on the bench; keeper redundancy, not an error.

### 4. Calibration log (2 GWs)

| GW | predicted XI | actual XI (pre-hit) | error |
|----|-------------|---------------------|-------|
| 1  | 55.31 | 84 | +28.7 |
| 2  | 59.01 | 48 | −11.0 |

Mean error +8.8, mean |error| ~20 — n=2, no level adjustment (GW1 note stands:
wait for 3–4 GWs). One structural observation to carry: the predicted LEVEL
rose 55.3 → 59.0 partly on noise-inflated components (Ekitiké 5.70, Ballard
4.10 — both 1-match artifacts per §2), so the two errors are not independent
draws around a stable mean. Log per-component bias again at GW3.

### 5. Improvement proposal (the one change): gate hits on MARGINAL ev_delta, not package ev_delta

- **File:** `src/fpl_claude/backtest/simulate.py`, `decide_transfers()` (the
  same policy home the live planner will reuse).
- **Bug mechanism:** the gate compares `result.ev_delta` — the WHOLE package's
  gain over rolling the squad — against `hit_ev_threshold`. Any forced or
  obvious free transfer (injury/suspension replacement — several per season,
  and their EV is further inflated by the overlay-horizon quirk in §2) raises
  package EV far above 4.5, and every marginal hit then rides through the open
  gate. GW2 is the proof: package +15.45 ≫ 4.5, while the hit itself was worth
  +2.48 — the policy in CLAUDE.md rule 5 ("never a hit below the EV
  threshold") was violated by construction, not by judgment.
- **Fix (~5 lines):** also solve hit-free, and require the hit transfers to
  pay for themselves:

  ```python
  result = optimize(..., max_transfers=state.free_transfers + max_extra_transfers)
  if result.hits > 0:
      free = optimize(..., max_transfers=state.free_transfers)
      if result.objective - free.objective < threshold * result.hits:
          result = free
  ```

  (objective already nets off `hit_cost`, so the threshold keeps its current
  net-of-hit semantics). Memos then quote the marginal number, which also
  fixes the misleading "+15.45" audit trail.
- **Testable, no future data:** unit test with a synthetic projections table
  where the best free move gains +12 and the best extra move gains +2 net —
  expect the free-only squad; +5 net — expect the hit kept. Deterministic,
  pure deadline-time inputs.
- **Why this over the GW1-flagged bench fix or the overlay-horizon fix:** it
  is the chokepoint every future hit flows through, and it is precisely the
  damper the noisy early-season projections need — churn driven by 1-match
  rates (§2) only hurts when it clears this gate. The bench fix's expected
  value fell on GW2's evidence (§3); the overlay-horizon fix is real but needs
  per-GW minutes structure (larger change, queued). Applied at GW2's deadline
  this fix keeps Wood and takes no hit — 3 pts worse in GW2 and still right.
- **Applies from GW3 onward; GW1–2 are not rerun.**

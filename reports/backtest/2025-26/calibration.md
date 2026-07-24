# Level / captain calibration — the 20-GW decomposition (defect A2)

*Resolves the `[OPEN] Level calibration` entry that the GW1–10 gate flagged and
every review since re-logged. Reproducible: `PYTHONPATH=src python
notebooks/calibration_analysis.py` regenerates every number below from the
committed `gwNN_players.csv` files. Error convention throughout:
**error = actual − predicted** (positive = the week out-scored the projection).*

## Decision: PATH A — close as process (ranking-correct, EV-reporting-only)

No model change. The prediction residual has **no stable, estimable, monotone
level bias** a calibration term could remove without either (a) being a proven
no-op on every pick and the hit-gate, or (b) risking the ranking that was
validated 20/20. The fix is a **reporting** one: the memo Outcome now logs the
predicted total split into **base XI + captain slot**, so EV and the hit-gate
margin are read against the known captain-slot variance instead of one opaque
number. Implemented forward-only (`predicted_xi_breakdown` in `simulate.py`,
`write_memo` Outcome line); committed memos are untouched.

This closure also **corrects an overstatement** the `[OPEN]` entry carried: the
mean under-prediction lives in the **base XI**, not the captain. The captain is
*mean-unbiased* (t = −0.06) and merely *high-variance*. "The doubled captain is
the entire variance" was half-right — it is the highest-leverage single slot,
but the ten non-captain players carry more of the total variance and all of the
(within-noise) mean bias. The decision is unchanged by that correction, and is
in fact more robust for resting on it.

## Method

- **Data.** The 20 committed `reports/backtest/2025-26/gwNN_players.csv` files
  (`id, web_name, team, position, price, predicted, actual, minutes, role
  [C/V/XI/bench], played_after_subs`), plus the single hit the season took
  (GW2, −4). No model code is imported — a pure post-hoc decomposition, so it
  stays valid verbatim as the live pipeline evolves.
- **The identity.** Every reported per-GW error decomposes exactly as

  `memo_err = base_XI_err + captain_slot_err + autosub_gain − hit`

  - `base_XI_err` — picked XI (11), captain counted **once**: Σ(actual−predicted)
  - `captain_slot_err` — the doubled **extra** copy: actual[eff C] − predicted[picked C]
  - `autosub_gain` — wedge: post-autosub XI actual − picked XI actual (≥ 0)
  - `hit` — wedge: −4 at GW2, zero every other week

  The script asserts this identity holds to `|residual| = 0.000000` and that its
  reconstructed totals equal the committed memo `predicted`/`actual` on all 20
  GWs. An interpretability re-cut splits the captain 0+2 instead of 1+1:
  **non-captain XI (10) + full doubled captain (2×)** — the split the memo line
  prints.
- **Honest wedges.** Predicted is the pre-autosub XI; actual is post-autosub and
  net of hits. Both wedges are tiny and bounded: autosubs added **+23 all
  season** (mean +1.15/GW, and 21 of those 23 came in just GW16 +11 and GW18
  +10 when a benched keeper/defender covered a surprise blank); hits were **−4
  total** (GW2). Neither distorts the base-vs-captain story.
- **Not in the CSVs (declared, not fabricated).** The CSVs store only the
  *total* predicted and actual per player, so a **bonus-component share** and a
  **home/away** split cannot be computed here without re-deriving projections;
  they are left as bounded notes, not invented. Per-**position** and per-**role**
  slices *are* fully supported and reported.
- The effective captain equalled the picked captain in **all 20 GWs** (no
  captain ever blanked to 0 minutes and handed the armband to the vice), so the
  captain-slot actual is unambiguous.

## Reconciliation (faithfulness check)

All 20 GWs reconstruct the committed memo numbers exactly (`predicted` to 2 dp,
`actual` to the integer); season actual sums to **1179**, matching the verdict.
The decomposition is therefore a faithful partition of the real reported error,
not an approximation.

## Season headline

| quantity | value |
|---|---|
| Σ predicted XI (incl. captain double) | 1076.2 |
| Σ actual (after autosubs & hits) | 1179 |
| 20-GW **mean** memo error | **+5.14** |
| 20-GW **median** memo error | +6.77 |
| base-XI error (captain ×1) | mean **+4.26**, std 12.63 |
| captain-slot error (extra copy) | mean **−0.07**, std 4.98 |
| non-captain XI error (10) | mean +4.33, std 12.24 |
| captain full error (2×) | mean −0.14, std 9.95 |
| autosub gain (wedge) | +23 total, +1.15/GW |
| hits (wedge) | −4 total (GW2) |

**The mean under-prediction is the base, not the captain.** And it is not
statistically distinguishable from zero (one-sample t over the 20 GWs):

| component | mean | SE | t (df=19) | significant at 5%? |
|---|---|---|---|---|
| base-XI err (cap ×1) | +4.26 | 2.90 | +1.47 | **no** |
| non-captain XI err (10) | +4.33 | 2.81 | +1.54 | **no** |
| captain-slot err (1×) | −0.07 | 1.14 | −0.06 | no (≈ 0) |
| captain full err (2×) | −0.14 | 2.28 | −0.06 | no (≈ 0) |

## Component statistics (20 GWs)

```
component                             mean  median     std     min     max     MAE
----------------------------------------------------------------------------------
memo_err (reported total)             5.14    6.77   14.77  -19.00   28.69   13.76
  base_XI_err (cap x1)                4.26    5.85   12.63  -16.65   28.58   11.81
  captain_slot_err (extra copy)      -0.07   -1.77    4.98   -7.34    7.35    4.46
  autosub_gain (wedge)                1.15    0.00    3.13    0.00   11.00    1.15
  hit (wedge)                        -0.20    0.00    0.87   -4.00    0.00    0.20
re-cut: noncap_XI_err (10)            4.33    2.26   12.24  -13.82   28.47   10.71
re-cut: captain_full_err (2x)        -0.14   -3.55    9.95  -14.68   14.70    8.92
```

## Variance decomposition (the "does the captain carry ~all the variance?" question)

Splitting the clean (wedge-free) error into non-captain-10 + captain-full-2×:

```
Var(non-captain XI, 10)      =   149.86   ( 68.5% of clean var)
Var(captain full, 2x)        =    99.05   ( 45.3% of clean var)
2*Cov(noncap, captain)       =   -30.23   (-13.8% of clean var)   <- they partly offset
Var(clean total)             =   218.69
Std(non-captain XI)  = 12.24   Std(captain full 2x) = 9.95   Std(clean) = 14.79
```

Counterfactual — how much of the reported spread is the captain?

```
Std(memo_err) as reported                 =  14.77
Std(memo_err) if captain slot were exact  =  12.46   (remove the extra copy's error)
Std(memo_err) if WHOLE captain were exact =  11.92   (remove both copies' error)
```

**Read.** The captain is the single highest-leverage *slot* (one player, doubled,
std 9.95 — no base player swings that hard, and removing it cuts season spread
from 14.8 → 11.9). But the ten non-captain players carry **more of the total
variance** (68.5% vs 45.3%; the negative covariance means base and captain
partly cancel week to week). So the tidy "captain = the entire variance" story
is not what the full sample shows. Both slots are large, roughly comparable, and
— critically — **both are outcome variance, not correctable bias**.

## Can an "environment-level calibration term" even work? No.

The `[OPEN]` entry proposed "scale raw xPts toward the realised league level."
The numbers say that is inoperable:

```
Std(predicted XI total)   =   2.96   (mean 53.8)     <- nearly flat every week
Std(actual XI total)      =  14.15   (mean 59.0)
Std(league GW average)    =   9.37   (mean 50.1)
corr(our predicted, league avg)  = +0.06
corr(our predicted, our actual)  = -0.11
corr(league avg, our actual)     = +0.73
```

Our predicted total is **nearly constant (std 2.96)** and has **~zero correlation
with the weekly slate** (+0.06 vs the league average, −0.11 vs our own outcome).
Our *actual* tracks the league slate (+0.73), but the prediction cannot see which
weeks run hot or cold — because that swing is player-level haul/blank variance
already conditioned on fixtures, not a level the model can anticipate. You cannot
scale a constant toward a level you cannot predict. A tighter prediction than
outcomes is the *correct* property of a mean estimate (Var(E[X]) ≤ Var(X)); the
weekly spread is irreducible, not miscalibration.

## Two tails — the extreme weeks, attributed

```
 GW memo_err base_err cap_slot cap_full autosub      cap   capd1x
-----------------------------------------------------------------
 11    -19.0    -15.6     -3.4     -6.8     0.0  Haaland     -3.4
 13    -15.4     -8.1     -7.3    -14.7     0.0  Haaland     -7.3
  2    -15.0     -8.9     -2.1     -4.2     0.0  M.Salah     -2.1
 12    -13.2     -8.5     -4.8     -9.6     0.0  Haaland     -4.8
  5    -11.8    -11.3     -0.5     -0.9     0.0  M.Salah     -0.5
 18    -11.7    -16.7     -5.1    -10.2    10.0  Haaland     -5.1
  6      1.9     -6.5      7.3     14.7     1.0  Haaland      7.3
  3      2.9      5.6     -2.7     -5.3     0.0  M.Salah     -2.7
 15      3.5      7.0     -4.4     -8.9     1.0  Haaland     -4.4
  9      4.0      9.3     -5.2    -10.5     0.0  Haaland     -5.2
  4      9.5      6.1      3.4      6.9     0.0  M.Salah      3.4
 17     11.5      4.4      7.1     14.3     0.0  Haaland      7.1
 19     11.8     15.6     -3.8     -7.6     0.0  Haaland     -3.8
  7     13.1     14.6     -1.4     -2.9     0.0  Haaland     -1.4
 20     13.3     17.8     -4.5     -9.1     0.0  Haaland     -4.5
 14     16.2      9.0      7.2     14.4     0.0  Haaland      7.2
 10     21.3     15.2      6.0     12.1     0.0  Haaland      6.0
 16     23.1      5.4      6.7     13.4    11.0  Haaland      6.7
  8     28.2     22.2      6.0     11.9     0.0  Haaland      6.0
  1     28.7     28.6      0.1      0.2     0.0  M.Salah      0.1
```

The tails are **mixed**, not captain-monopolised. The three biggest positive
weeks are base-driven: GW1 +28.7 (captain +0.2 — a whole defence + attack
clicking), GW8 +28.2 (base +22.2), GW19/GW20 (base +15.6/+17.8, captain
*negative* — the AFCON base out-hauling while Haaland blanked). The captain
owns the GW14/16/17 hauls (Haaland 28/26/32) and deepens the GW13/18 troughs.
The negative weeks (GW11/12/13/18) are both slots down together. No single slot
"explains" the error; both are irreducible variance around a well-centred mean.

## By position (per-player, pooled over 20 GWs of picked XI)

```
              picked XI (all)            starters only (min >= 60)
position    n  mean_err   MAE           n  mean_err   MAE
------------------------------------    ------------------------
GKP        20    +0.44   2.34          20    +0.44   2.34
DEF        74    -0.04   2.68          60    +0.66   2.60
MID        83    +0.90   3.36          76    +1.22   3.32
FWD        43    +0.12   3.99          38    +0.36   4.30
ALL       220    +0.39   3.16         194    +0.80   3.19
```

Non-captain starters (min ≥ 60): mean err **+0.90**, MAE 3.04. Captain single:
mean **−0.07**, MAE 4.46, std 4.98.

The only per-player signal worth a footnote is **starting midfielders +1.22**
(mean_pred 4.20 → mean_act 5.42) — consistent with the note that the **bonus90
proxy has had no new signal since GW1** and that attacking-mid ceilings
(assists, bonus) are mildly under-weighted. But (a) it is small and borderline,
(b) at the XI level minutes misses on rotated starters drag the base back down
to +4.3, and (c) a per-position bump is exactly the kind of **non-uniform**
change that would reorder MID-vs-FWD in XI/captain selection and could break the
20/20 ranking. Left `[WATCH]` for a Minutes-v2 / bonus-model pass, not built here.

## Why not Path B — refuted point by point

1. **No stable bias to estimate.** Base +4.26 is t = 1.47 (not significant,
   df = 19); the captain is dead-on zero-mean (t = −0.06). The "bias" is within
   sampling noise over 20 GWs.
2. **A uniform additive calibration is a *proven no-op* on every decision.** The
   MILP objective sums, for any feasible squad, `Σ_XI score + Σ_cap score +
   VICE·Σ_vice + BENCH·Σ_bench(4)`; adding a constant *k* to every player shifts
   *every* candidate by the same `(11 + 1 + VICE + 4·BENCH)·k` → argmax
   unchanged (same squad, XI, captain, bench) and it cancels in the marginal-net
   hit-gate (`result.obj − free.obj`). A uniform level correction would move the
   printed EV and change **nothing** we decide — so it belongs in *reporting*,
   which is exactly Path A.
3. **A multiplicative "scale toward the league level" would *corrupt* the
   hit-gate.** It scales the point-gain but not the fixed −4 cost, so a within-
   noise +4 bias inflated by a ~1.1× scale flips borderline hits from reject to
   accept — a decision change driven by noise, in the one place the calibration
   was said to matter. And it is inoperable anyway (corr +0.06 with the level).
4. **No captain-ceiling mean to fix.** The captain is mean-unbiased; raising its
   mean prediction would *introduce* bias. Its issue is variance (which you
   cannot predict away without knowing which week Haaland returns 32 vs 2).
5. **Ranking is the asset to protect.** Every relative call validated, captaincy
   20/20. A model change that could reorder picks trades a *reporting* gain for
   *ranking* risk — the wrong trade.

## What was implemented (Path A, forward-only)

- `simulate.py`: `predicted_xi_breakdown(squad, projections, gw, chip)` →
  `XiBreakdown(total, base_xi, captain_slot, captain_mult)`; `predicted_xi_points`
  now delegates to it (identical return, tests unchanged). `GWResult` carries
  `base_xi_pts / captain_slot_pts / captain_mult`; `run_gameweek` populates them.
- `run.py` `write_memo`: the Outcome line now reads
  `Predicted XI points: **T** = base XI B + captain slot S (doubled|tripled)`
  with a one-line pointer to this file. Committed `gwNN.md` are **not**
  regenerated — the format applies from the next simulated GW (GW21) onward.
- Test: `tests/test_chips.py::test_predicted_xi_breakdown_splits_base_and_captain`
  (normal / triple-captain / bench-boost arithmetic; base + slot == total).
- `.claude/skills/fpl-review/SKILL.md` calibration step aligned to the corrected
  story (log **both** base and captain slot; the base carries the small mean,
  the captain the variance).

*History for this defect lives in `reviews/gw10–gw20.md` (the per-week
calibration logs). This file is the distilled resolution.*

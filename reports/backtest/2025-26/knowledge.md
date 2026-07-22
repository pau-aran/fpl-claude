# Knowledge base — living document

*Distilled, current truths only — NOT a log. Each weekly review adds, updates,
or REMOVES points here; superseded/disproven points are deleted, not archived
(history lives in `reviews/gwNN.md`). Tags: [DONE]=encoded in code/process,
[OPEN]=known defect awaiting fix, [WATCH]=hypothesis needing more evidence.*

## Modeling

- [DONE] Tiny samples explode per-90 rates: pseudo-minute shrinkage
  (`SHRINKAGE_MINUTES=90` in rates.py). A 1-minute cameo is not a 5.4 xG/90.
- [DONE] Team ratings need ≥5 matches (`MIN_TEAM_MATCHES`); promoted teams run
  on FDR fallback until ~GW6 — one opening 3-0 is not a rating.
- [DONE] A stat with no prior era (DC before 2025/26) must not be shrunk
  toward its phantom-zero prior column.
- [DONE] Overlays are time-scoped via `duration_gws` (projections.py, from
  GW5): a one-week doubt suppresses 1 horizon GW, clean estimate beyond.
  Fixed the season's binding constraint (three phantom-sell scalps GW2–4).
  First live week (GW5) clean: Saliba scoped 1 GW at 0.55 → predicted 1.96
  / actual 2, horizon recovered, NO phantom sale proposed — first proposal
  in five weeks with unpoisoned inputs. SAFETY DEFAULT: omitted duration =
  whole horizon (an ACL/departure must not "recover") — short durations are
  OPT-IN per entry (knock → 1-2, "weeks" → 3-4, ban → matches left,
  structural/long-term → omit; scoping only matters for suppressions,
  near-1.0 confirmations may omit).
- [OPEN] Minutes model turns 1 start into p_start=1.0 for no-prior players
  (`_start_share`). Ballard: fielded 0-min GW2–4 (10.47 predicted pts for
  8 real minutes) — but self-correcting (4.10→2.42 as team_games grows)
  and hasn't driven a transfer since GW2. Demoted behind overlay-horizon.
- [OPEN] `low_sample` is flagged but nothing consumes it: a newcomer's
  one-match rates outrank an established player's blended prior (Ekitiké 71'
  vs Wood's 20-goal season). Confidence haircut on horizons wanted.
- [WATCH] Level calibration: 5-GW mean error +2.9 (excl GW1: −3.6, n=4) —
  no level bias, no adjustment. Predictions sit flat 51–59 while actuals
  track the LEAGUE environment (official avgs 54/51/48/63/42 vs our
  84/44/54/61/40): big misses are slate-wide hot/cold weeks, not model
  level. Bonus proxy: no new signal since GW1. DC: first threshold points
  banked GW5 (Gudmundsson +2, Semenyo +2, three near-misses) — the
  "DEF picks under-index CBIT" worry weakened, watch continues.

## Decision policy

- [DONE] Hits are gated on MARGINAL NET EV per hit: the hit solution must
  beat the best hit-free solution by ≥4.5 per hit WITH the -4 already
  charged. Package deltas smuggle sub-threshold hits (GW2's Wood sale), and
  a first implementation at net ≥0.5 would have re-passed it (GW3 review
  catch) — semantics now in code and both rules files. Verified live GW4
  (quoted net +5.76 correctly); remaining exposure is poisoned INPUTS from
  the overlay-horizon defect, not the gate.
- [DONE] The optimizer output is a proposal. Manager overlay (lock/ban/
  captain/cap, written reasoning) is mechanical via `--decision`.
- Premium assets are holds through short knocks — never sell a talisman at
  the bottom of his value on 1-2 week news (GW3: held Palmer).
- Buy RUNS of fixtures, not single GWs; plan 2-3 week transfer paths; enter
  one GW before a run turns good (Haaland queued for City's GW6 BUR(H)).
- Never re-buy what you just sold without new information — churn admits the
  first move was wrong and pays spread twice (GW3 veto of Wood buy-back).
- A hit that clears the EV gate can still be WRONG if it damages the
  standing multi-week plan (burns the bank a planned double-move needs,
  spends a banking FT, buys what the plan replaces). Every hit is checked
  against `plan.md` before approval; plan-conflicting hits need BOTH the EV
  gate and an explicit written reason why breaking the plan is worth it.
- [WATCH] Playable-bench EV: positive but small; mixed evidence (GW1 zero
  coverage cost an autosub; GW2 best enabler scored −1). Bought Gudmundsson
  GW3 as 15th man.
- A lock/cap re-solve can silently redirect the transfer away from the move
  the written reasoning described (GW4: approval text argued for Senesi, the
  constrained solve bought Calafiori) — re-read the constrained solution and
  amend the memo before sign-off.
- Captaincy = highest projection unless news says otherwise: passed review
  5/5 weeks (Salah ×5). The rule handles form shifts by itself — the model
  already cooled Salah (27.7 horizon) through his four single-digit weeks
  and hands Haaland the GW6 armband mechanically once he enters. No recency
  overrides.
- Community consensus (X strategy accounts, r/FantasyPL GW threads, FFScout
  polls) is a decision INPUT from GW6: a candidate roadmap plus effective-
  ownership risk context (a template move we skip is a rank bet; a
  differential we take needs conviction). Never an order — diverging from a
  clear template move requires a written reason in the memo, and so does
  following one the models dislike. Weekly `consensus/gwNN.md`, pre-deadline
  sources only.

## Season context (2025/26 replay, verified)

- Official GW averages 1–10: 54, 51, 48, 63, 42, 46, 60, 56, 46, 65 (cum 531).
- Pep rotation is priced into nothing: don't double City defenders without a
  written rotation overlay (GW1 Gvardiol).
- Availability news beats every model input: the overlay layer (researched,
  pre-deadline-sourced only) is the biggest single edge in GW1's +30.

## Backtest fidelity (methodology)

- vaastav `players_raw.csv` is end-of-season state — team/position/prices
  must come from `merged_gw` at-or-before the GW (January transfers leak).
- No historical injury flags exist: consecutive-blank proxy + researched news
  overlays stand in; keeper competitions encoded as probabilistic splits.
- Improvements apply forward only; completed GWs are never rerun.

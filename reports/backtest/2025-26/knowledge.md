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
- [OPEN] One-GW availability overlays zero the ENTIRE horizon: a 1-2 week
  knock is priced as an 8-GW absence, inflating forced-move EV ~4x (GW2:
  "+15.45" that was really ~+4). Needs per-GW minutes structure.
- [OPEN] Minutes model turns 1 start into p_start=1.0 for no-prior players
  (`_start_share` trusts any team_games>0 without a prior). Ballard: bought
  on it GW2, benched GW2 AND GW3 while we fielded him at 3.95 — two weeks of
  direct cost, now the top open defect.
- [OPEN] `low_sample` is flagged but nothing consumes it: a newcomer's
  one-match rates outrank an established player's blended prior (Ekitiké 71'
  vs Wood's 20-goal season). Confidence haircut on horizons wanted.
- [WATCH] bonus90 prior-proxy runs light (XI took 12 bonus in GW1); DC now
  flows post-fix. Log per-component bias each week before touching levels.

## Decision policy

- [DONE] Hits are gated on MARGINAL NET EV per hit: the hit solution must
  beat the best hit-free solution by ≥4.5 per hit WITH the -4 already
  charged. Package deltas smuggle sub-threshold hits (GW2's Wood sale), and
  a first implementation at net ≥0.5 would have re-passed it (GW3 review
  catch) — semantics now in code and both rules files.
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
- Captaincy = highest projection unless news says otherwise: passed review
  3/3 weeks (Salah ×3).

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

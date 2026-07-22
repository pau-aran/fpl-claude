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
- [DONE] Newcomer confidence haircut (`shrink_newcomers`, rates.py, from
  GW8): a priorless newcomer has nothing for `blend` to regress toward, so
  his small-sample rates rode at full trust and a 2-game hot streak outranked
  an established player's blended prior. Now priorless players are regressed
  toward a positional replacement baseline (30th-pct of established players
  at that position) by their `evidence` weight (min(1, mins/540)), heaviest
  with least evidence, decaying to nothing at a full sample. Verified GW8:
  Woltemade xg90 0.44→0.27 (ev .56), Ekitiké 0.37→0.27 (ev .71); Gyökeres
  (full sample) and Isak (has a prior → blend handled him, NOT double-shrunk)
  untouched — exactly the set that should/shouldn't move. Directly de-risks
  the Woltemade-type bandwagon the market pushed at GW8.
- [WATCH] Level calibration: 8-GW mean error +7.2, mean |error| 13.9. Two
  large UNDER-predictions in a row (GW7 +13, GW8 +28) as the environment ran
  hot (official avgs 60, 56) and our captain+defence hauled. Predictions sit
  flat 51–59 while actuals swing with the league (official
  54/51/48/63/42/46/60/56 vs our 84/44/54/61/40/55/71/82). This is
  totals-COMPRESSION, not ranking bias — the model still ordered buys right
  (Fernandes>Saka confirmed GW8), so no adjustment yet. IF under-prediction
  persists a 3rd week, test whether horizon decay / a minutes ceiling is
  systematically clipping high-scorers. Bonus proxy: no new signal. DC watch
  continues.

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
  one GW before a run turns good (Haaland entered GW6 BUR(H) ahead of the
  865k rush: 16 pts, captained — the pattern's first full payoff).
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
- Bench policy (owner directive, 2026-07-22): the second GK is a dead slot
  most weeks — spend the minimum there. Outfield bench occasionally matters:
  when a transfer choice is otherwise close, prefer budget players whose
  fixtures COMPLEMENT an existing bench piece across GWs (bench rotation) —
  and a single signing that completes such a pair gets the nod over an
  equivalent one that doesn't. Strictly a tie-breaker: bench rotation never
  outranks XI quality ("team sanity" first).
- A lock/cap re-solve can silently redirect the transfer away from the move
  the written reasoning described — twice now (GW4 Senesi→Calafiori; GW6
  reasoned Ekitiké route → plan-primary Salah route). The post-solve
  re-read + signed addendum caught both; control judged SUFFICIENT. No
  lock-the-reasoned-route solver mode: GW6's redirect was arithmetically
  FORCED (Ekitiké £8.7 + bank £0.5 = £9.2 vs Haaland £14.3; no 2-FT repair
  passes the FWD quota) — a locked route would deadlock at the deadline or
  force a forbidden hit. Instead: a written funding route must SHOW ITS
  ARITHMETIC (sells + bank ≥ buys; resulting squad quota-legal) before the
  solve runs. Re-judge only if a redirect ever slips through un-caught.
- Purist matchup lens (owner directive, 2026-07-22): every deadline, write a
  short POSITIONAL-DUEL read alongside the quant inputs — in-form players who
  come up against a weak direct counterpart in their position (winger vs a
  slow/exposed fullback, striker vs an error-prone CB pairing or a stand-in,
  attacking fullback vs a winger who doesn't track back, defence/GK vs a
  blunt attack). Team-level FDR misses these: a "hard" fixture can hide a
  soft individual duel and vice versa. Use it (a) to seed candidate
  shortlists the model underrates, (b) as the tilt on close calls —
  captaincy tiebreaks, ordering between near-equal transfer targets, XI
  bench-order calls. It NEVER overrides the EV gate, the plan, or minutes
  risk — it's the creative overlay on top, and the duel named must be
  written in the memo so the review can grade it.
  [WATCH] First live outing GW7 (3 duels named): all reads were
  matchup-correct (Mbeumo v Reinildo-less Sunderland +6; Ekitiké-fade
  congruent with the benching; Semenyo home 18) BUT every one only agreed
  with signals we already had (FDR, ownership, overlay) — it has not yet
  surfaced a player the model UNDERRATED, which is its purpose. The real
  test is the first DIVERGENCE (lens says buy, model is cold). Cost nothing;
  keep grading live.
- Captaincy = highest projection unless news says otherwise: 8/8 (Salah ×5,
  Haaland ×3). GW8 Haaland v EVE(H) — 71% poll, goal+assist+bonus, doubled 26.
- Value over reputation beats consensus template adds when the model
  disagrees on minutes/underlying: GW8 faded the most-bought Saka (model
  horizon 17.0) for B.Fernandes (23.95) — the crowd was SELLING Fernandes
  (~240k out), so buying the sentiment low was contrarian value. Outcome:
  Fernandes 8 > Saka 7, £0.9 cheaper. Never override a large horizon gap
  (here 7 pts) on a reputation narrative; the duel lens is a tie-breaker, not
  an override. The armband migrated mechanically the week Haaland entered
  (8.65 top of board → returned 16→32) — the rule handles form shifts by
  itself. No recency overrides.
- Community consensus (X strategy accounts, r/FantasyPL GW threads, FFScout
  polls) is a decision INPUT from GW6: a candidate roadmap plus effective-
  ownership risk context (a template move we skip is a rank bet; a
  differential we take needs conviction). Never an order — diverging from a
  clear template move requires a written reason in the memo, and so does
  following one the models dislike. Weekly `consensus/gwNN.md`, pre-deadline
  sources only. First live week (GW6) was too convergent to test it
  (model and 67% poll agreed on Haaland); its first real test is the one
  divergence taken — Palmer hold vs mass sells — resolving GW8.

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

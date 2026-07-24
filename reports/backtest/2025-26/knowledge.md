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
- [DONE] Minutes model no longer turns 1 start into p_start=1.0 for no-prior
  players. The `_start_share` no-prior tiny-sample branch used to return raw
  `starts/team_games` (Ballard: 10.47 predicted pts for 8 real minutes, GW2–4).
  Now it shrinks toward `NEUTRAL_START_SHARE` by `team_games/3`, mirroring the
  prior-blend branch — heaviest with least evidence, gone by `team_games ≥ 3`.
  Low steady-state impact (self-corrected by ~GW4-5), but it de-risks GW1–3 of
  the first post-WC-2026 season, exactly the small-sample/no-prior window where
  it bit before overlays are written.
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
- [OPEN] Level calibration — VARIANCE-BOUNDED not monotonic (13-GW mean error
  +1.5), and the residual concentrates in the DOUBLED CAPTAIN SLOT. The model
  under-predicts TOTALS ~15–25% in strong weeks (GW7–10 +13/+28/+4/+21) but
  over-predicts on dead slates: GW11 −19, GW12 −13, GW13 −15 (THREE straight), all
  driven by the captain (Haaland) blanking — a pen miss then two no-returns. The
  model doubles the captain's ~7-9 projection, so consecutive captain blanks
  mechanically gut the predicted total while the rest of the squad tracks close to
  prediction. So it is a captain-ceiling / bonus-signal defect that amplifies in
  BOTH tails, not a fixed +offset — concentrated in the captain slot specifically.
  (GW14 flipped straight back to +16 under-prediction the moment the captain
  returned 28 — the base XI is well-calibrated, the doubled captain is the variance.)
  GW17 confirmed it a third time: predicted 58.5, actual 70 (+11.5), of which the
  captain alone (Haaland 17.7 predicted → 32 actual) was +14.3 — the rest of a thin XI
  under-scored, netting the base to slightly OVER-predicted. 17-GW mean error +4.2.
  GW18-20 confirmed BOTH tails inside three weeks: GW18 −11.7 (captain blank guts the
  total), GW19 +11.8 and GW20 +13.3 (base XI out-hauls — Rice/Thiago/Enzo/Timber/Tarkowski
  big returns — while the captain STILL blanks). 20-GW mean error ~+4.0. Haaland returned
  2/2/2 across the AFCON-window openers (four straight captain blanks GW17-excepted); the
  base XI is well-calibrated in ranking (every relative call validated, captaincy 20/20),
  the doubled-captain slot is the entire variance.
  It is NOT a ranking bias — every relative call was validated (Fernandes>Saka,
  Mateta/Konaté/Enzo/Thiago, captaincy 14/14) — so it never hurt a DECISION, but it
  distorts EV reporting and the hit-gate margin. LIVE FIX: an environment-level
  calibration term (scale raw xPts toward the realised league level) and/or better
  captain-ceiling + bonus modelling (the bonus proxy has had no new signal since
  GW1). Applies forward-only.
- [DONE — split fix] Bench-order leak (was [OPEN — PRIORITY], the biggest
  recurring leak — GW10 −3, GW13 −8, GW17 −3). Root cause was TWO problems under one
  label: (1) the optimizer picked the XI/captain/bench on `xpts_horizon` (a decayed
  MULTI-week total) while the week is scored on the single next GW — GW10 benched
  Saliba behind Senesi on the horizon though the immediate GW ranked Saliba higher;
  GW17 benched Saliba (6) behind Tarkowski because a returning player's minutes
  projection stays low for 1-2 GWs. FIXED: `optimize()` now derives XI/captain/vice/
  bench on the nearest `xpts_gw{n}` column (auto-detected; `_pick_lineup` in milp.py),
  squad-15 and transfers still on the horizon; applies forward-only (GW18+). (2) GW13's
  −8 was a projection the model can't fix — it rated Calafiori over Konaté on the
  immediate GW too, blind to Arsenal's depleted back line; no lineup re-rank catches
  that. FIXED via the manager overlay: `ManagerDecision.start`/`bench` (decision JSON
  `start`/`bench`) force an owned player into/out of the XI with written reasoning — the
  bench-order override the reviews asked for. Deliberately NOT done: a team-model
  CS-probability overhaul to cure defender fixture-compression — over-engineering,
  left [WATCH].
- [PROCESS] The bench-order OVERRIDE only helps if the manager pulls it. GW19: our own
  pre-hoc duel read named Konaté the softest CS bet (LIV v Leeds H), the solver benched him
  on a 0.06 hair, he returned 7 on the bench (started Senesi 3) — the `force_start` lever
  existed and was NOT used (~−4). RULE (GW20+): when the duel lens names a prime CS/attacking
  bet that the solver benches on a <0.2 xpts hair, pull `force_start`. This is a discipline
  point, not a code defect (the model's own order was a coin-flip); it complements the
  [DONE] split fix. Watched clean at GW20 (no lever owed).
- [PROCESS] Suspension verification: a ban needs the OFFENCE **and**
  confirmation it was upheld/served against the team sheet — not an aggregator
  headline. The GW9–10 Ballard "3-match ban" was misapplied (he played both
  weeks; harmless only because he was benched/outscored anyway). Default to
  AVAILABLE when the primary source is ambiguous — an erroneous 0.0 could bench
  a real starter in a costlier spot.

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
  [PROVEN] Reads 7-for-7 weeks matchup-correct through GW13, and TWO independent
  buy-side divergences have now cashed: GW12 Enzo at Burnley (11, a crowd-sold mid
  on a soft duel) and GW13 Thiago v Burnley (13 on debut, an in-form No.9 vs the
  league's most porous side). Two hits was the pre-set threshold — the duel lens
  is now a validated buy-side EDGE, not merely a hold/captain-context tool. It
  still never overrides the EV gate, the plan, or minutes risk; the named duel is
  written in each memo for grading. Keep grading live; watch for the first MISS to
  size its false-positive rate.
- Captaincy = highest projection unless news says otherwise: 20/20 rule
  adherence (Salah ×5, Haaland ×15). The AFCON window opened with a captain DROUGHT —
  Haaland 2/2/2 across GW18-20 (four low weeks in the last five, GW17's 32 aside), yet he
  was the top projection + ~90% EO shield EVERY week, so no recency switch was ever right
  (a switch chases a moving target AND the ~90%-owned field bleeds the identical blanks —
  averages 44/40/42). The rule is judged on adherence; the drought is the calibration
  [OPEN]'s captain-slot variance. The GW14/16/17 hauls (28/26/32) all landed the week AFTER
  a drought stretch — holding through is what catches them. Haaland RETURNED 26 at Palace (GW16) — the
  4-in-5 blank streak was pure variance, and holding the shield through it (no
  recency switch) caught both GW14's 28 and GW16's 26. Haaland has blanked FOUR of the last FIVE as
  captain (GW11-13, GW15; only GW14's 28 broke it) — extraordinary variance, but he
  was the top projection + ~90% EO shield EVERY week, so a recency switch would have
  (a) missed the GW14 haul and (b) chased a moving target. The rule is judged on
  adherence; the streak is the calibration [OPEN]'s captain-slot variance, not a
  process flaw. Discipline (no recency switch) explicitly tested and held.
- Hold premiums through SHORT-TERM absences; refuse lateral swaps to patch one week.
  GW14: with Saliba ill (out ~1wk), Senesi + Brooks banned (1 game), Thiago benched
  (tactical), the solver offered a free cost-neutral Saliba→Virgil. Refused — a
  lateral premium-CB swap on a one-week illness burns an established hold + the
  banked FT to fix a single thin XI. Accepted a legal-but-thin 3-4-3 (benched Thiago
  the forced 10th) instead; it cost ~0 (Thiago still played 30'). Bank the FT, let
  the absentees return. (Distinct from a forced injury replacement like Semenyo→Enzo,
  where the loss was multi-week + AFCON.)
  [PROVEN twice more, GW19-20] Two "hold" flavours both cashed in the same block: (a) GW19
  BENCHED Rice on a 1-week precautionary knee (Arteta short-term) rather than churn a PS7.2
  anchor — he returned 17 on GW20; (b) GW20 HELD Enzo through his one hard fixture (MCI-A,
  FDR5) rather than move-and-move-back — he returned 11 at the Etihad. The multi-week/AFCON
  cutoff for a forced SALE vs a 1-week BENCH is the whole discipline: Calafiori (month) sold,
  Rice (1 week) benched. Selling+rebuying for a single week burns an FT and pays spread twice.
- Transfer SEQUENCING: enter a fixture run one GW early, but NOT into the
  target's worst fixture. GW9 deferred Ekitiké→Mateta because Mateta's GW9
  was ARS(A) (his worst) — outcome Mateta 2 = Ekitiké 2 (zero cost), banked a
  2nd FT for GW10 where his run turns green. Don't pay a hit or take a bad
  entry week for a horizon edge that lives later in the run.
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

- Official GW averages 1–20: 54, 51, 48, 63, 42, 46, 60, 56, 46, 65, 38, 39, 35, 58, 49,
  60, 66, 44, 40, 42 (cum 1002). GW18-20 (44/40/42) is the low AFCON+festive trough — the
  crowd is weak here, so value holds + patience compound the edge (we went +42 over these 3).
- **AFCON: PL players unavailable from GW17** (starts 21 Dec 2025; min 3 GWs, some
  6). Owned asset = Mbeumo (Cameroon); available GW15-16, gone GW17+, **back GW22**. HOLD him
  through his good GW15-16 fixtures, move at GW16-17 into a NON-AFCON mid (don't sell
  early — GW15 Mbeumo returned 8 at Wolves after we refused the premature sale).
  Salah (Egypt, deeper run) out GW17-22, **back GW23** — not owned. The archive-blind model
  proposes buying AFCON players back EVERY week (status stays 'a') — BAN them until confirmed
  back. Never buy a mid/fwd about to vanish without pricing the gap.
- **Ghana did NOT qualify for AFCON 2025** — Semenyo (Ghana) was fully available all window
  (90 min every GW), which is why he was the value cover for Bruno at GW18. Don't assume an
  African player is AFCON-bound; verify the nation qualified AND he was called up.
- **Festive congestion (GW18-20 in 9 days, 26 Dec/30 Dec/3 Jan) breeds surprise blanks and
  warm-up injuries.** Point-in-time nuance: the FPL deadline is 90m before the round's FIRST
  KO, which can be a day+ before a given club's game — an injury in that club's warm-up
  (Calafiori before the GW18 Brighton game, ~20h post-deadline) is NOT knowable that week and
  becomes next week's forced sale. Hold the honest read; autosubs + a legal bench cover it.
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

# Model fixes — closing the season-rollover defects

*2026-07-25. Closes the defects raised in [`projections-run.md`](projections-run.md),
whose own conclusion was "don't run the optimizer against this yet".*

All of them had one root cause: **the prior layer could not tell "played and was bad"
from "barely played" from "played for a different club".** At a season rollover, where
the current season has zero minutes and the prior carries 100% of the weight, that
distinction is the whole model.

## D3 — a prior ROW is not a prior SAMPLE *(fixed)*

~50 players had a prior row of all zeros — on loan abroad, injured from August,
third-choice keeper — and `rates.blend` weighted it 1.0 pre-season. Rashford carried
`xg90 = xa90 = 0.00` at £7.0m as if it had been *measured*.

**Fix:** the prior now carries its own weight, `prior_strength`, ramping 0 → 1 over
`PRIOR_FULL_WEIGHT_MINUTES = 900` (ten full matches — the point at which a per-90 rate
stops being dominated by `SHRINKAGE_MINUTES`). At zero prior minutes the row earns
strength 0 and its owner is handled exactly like a priorless newcomer: the weight goes
to the positional replacement baseline instead of to a confident zero.

## D2 — thin priors read as confident *(fixed)*

Isak — Liverpool's first-choice No.9 — projected **5.35 xPts over 8 GWs** off 694
minutes wrecked by a fibula fracture, with `low_sample` reading **False**. The table
presented a guess with the same face as a 3,000-minute season.

**Fix, two parts:**
1. The shortfall `1 − evidence` is now spent on the positional baseline for *every*
   under-evidenced player, not only priorless ones (`shrink_newcomers`). Baselines are
   computed from **fully** evidenced players only, so a cohort of thin-prior newcomers
   cannot drag down the bar they are then measured against.
2. `low_sample` is now `evidence < 1.0`. Pre-season an established player scores exactly
   1.0 (no current minutes, full-weight prior) so his flag stays off, and the flag lights
   up precisely on the thin-prior players whose confident-looking numbers were the defect.

## D4 — the club-change blind spot *(fixed)*

Dubravka ranked **#1 in the entire game by xPts/£m**: a £4.0m player who is Spurs' likely
*backup*, carrying 35 starts made for **Newcastle**. `minutes-blindspots.md` had already
identified this class — 27 players who have a prior but changed club, where the model is
*confidently wrong* rather than merely uncertain.

**Fix:** the minutes prior is no longer a bare float. `StartSharePrior` carries the share
*with the evidence behind it* — the minutes, and the `team_code` it was earned at (stable
across seasons). `_discount_prior` then applies two independent regressions toward neutral:

| Discount | Trigger | Rationale |
|---|---|---|
| **thin** | `minutes < 900` | A share cannot distinguish a benched player from an injured one |
| **new club** | `prior.team_code != current` | Evidence about the player, not about his place in *this* pecking order |

Both apply, so a thin prior at a new club is discounted twice. Confidence is surfaced as
`prior_thin` / `prior_new_club` so the overlay work-list is visible in the table rather
than reconstructed by hand.

## Regression check — the gate is not broken

These layers carry the PLAN §4 backtest gate (2025/26 GW1–10: 624 vs 531 baseline), so
the change was replayed against it rather than assumed safe.

| GW | Original run | After fixes | Avg manager |
|---|---|---|---|
| 1 | 84 | **84** | 54 |
| 2 | 44 | 43 | 51 |
| 3 | 54 | 71 | 48 |
| 4 | 61 | 72 | 63 |
| 5 | 40 | 37 | 42 |
| 6 | 55 | 59 | 46 |
| **Σ1–6** | **338** | **366** | **304** |

GW1 reproduces **exactly** (84), which is the meaningful identity check: at full prior
strength the new arithmetic is identical to the old, so an established player's numbers
do not move.

**Honest caveat on GW2–6.** This is a directional check, not proof. The original run's
decisions were made by a manager in the loop responding to *that* run's proposals; here
the same overlay and decision files were replayed against a changed model, so the squad
paths diverge after GW1 and the later gameweeks are not strictly comparable. The claim
supported is the negative one — **no degradation** — not "+28 of new edge".

## Not fixed, and why

- **D1 — injury flags priced as 8-GW absences.** 20 `d`-flagged players carry a 25%
  haircut across the whole horizon from a July knock, 27 days before the deadline.
  `duration_gws` exists but only for manual overlays. Inferring a duration from a bare
  `chance_of_playing` would be speculation dressed as data; the honest fix is that the
  manager scopes it in the overlay, which [`decisions/overlays/gw01.json`](../../decisions/overlays/gw01.json)
  does for every flagged player we care about. **Left open and documented.**
- **D6 — team-model name matching.** Ipswich falls back to FDR because of a name
  mismatch (`Ipswich` vs `Ipswich Town`), not by design, and `TeamModel.covers()` counts
  matches without checking their **age**, so a club with only a stale relegation-season
  history would be silently modelled as current. For GW1 the FDR fallback on a promoted
  club is the conservative outcome, so this is not on the critical path — but the age
  check is a real latent bug. **Left open.**

## Incidental bug found and fixed

`backtest/run.py` and `reports/team_week.py` wrote markdown with `Path.write_text` and no
`encoding`, i.e. the platform default. On Windows (cp1252) any memo containing an accented
name or the `→` transfer arrow raised `UnicodeEncodeError` **after** the gameweek had been
simulated and the state advanced — a corrupting failure, not a cosmetic one. It blocked
this very regression run at GW2. Now explicit UTF-8.

**112 tests green, ruff clean on the repo's configured selection.**

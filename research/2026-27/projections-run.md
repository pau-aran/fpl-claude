# Projections pipeline — first live 2026/27 run

**Snapshot:** `db/raw/2026-07-25/` (558 players, 20 teams, 380 fixtures, GW1 deadline
2026-08-21) · **Run date:** 2026-07-25 · **Horizon:** 8 GWs (GW1–GW8, 80 fixtures, no
blanks or doubles)

```
./.venv/Scripts/python.exe -m fpl_claude.models.projections \
    --from-snapshot 2026-07-25 \
    --prior-season-csv db/vaastav/2025-26/players_raw.csv \
    --horizon 8
```

Output: `db/projections/2026-07-25.csv` (gitignored, regenerable).

**Rules engine was not a blocker.** `config/rules/2026-27.yaml` reports
`verified: True, unverified sections: []`, and in any case the projections layer never
gated on verification (only the optimizer does). No override was needed and the file was
not touched.

---

## 1. The blocker that was fixed: cross-season id remapping

Every 2026/27 stat in the snapshot is zero — no matches have been played — so the whole
pipeline is a prior-propagation exercise. The prior arrives via `--prior-snapshot`, which
joins on the element `id` field. **FPL reassigns element ids at every season rollover**, so
pointing that flag at last season's bootstrap does not fail loudly; it attaches the wrong
player's entire history to every row and produces a full, plausible-looking table of
garbage.

New module `src/fpl_claude/data/season_bridge.py` builds the prior from a completed
season's vaastav `players_raw.csv` and remaps ids through **`code`**, the permanent
cross-season player key. Same approach as
`backtest/data.py::SeasonStore.prior_bootstrap()`, deliberately not coupled to it — the
backtest package stays untouched.

- Carries exactly what the model layers read: `minutes`, `starts` (→
  `minutes.priors_from_bootstrap`); `expected_goals`, `expected_assists`, `saves`,
  `defensive_contribution`, `bonus` (→ `rates.from_bootstrap`); plus `element_type`,
  `web_name`, `code` for diagnostics.
- **Players with no prior row are dropped, not zero-filled.** A zeroed prior reads as
  "played and produced nothing"; absence reads as unknown, which is what
  `rates.blend` / `shrink_newcomers` / `minutes._start_share` are built to handle.
- A *missing column* (e.g. `defensive_contribution`, which did not exist before 2025/26)
  becomes 0, not NaN — a NaN would silently void every per-90 for that player.

Pipeline wiring in `models/projections.py`:

| Flag | Join key | Use for |
|---|---|---|
| `--prior-snapshot PATH` | element `id` | a bootstrap from **earlier this season** (unchanged behaviour) |
| `--prior-season-csv PATH` | `code` → current `id` | a **completed season's** `players_raw.csv` |

The two are mutually exclusive. `--prior-snapshot` now also runs
`_warn_if_ids_reassigned()`: both payloads carry `code`, so if the id→code maps disagree
on >10% of shared ids the run prints a loud warning that the snapshot is from another
season. That is the trap this whole exercise exists to close, and it should not be
possible to walk into it silently again.

Two Windows-console fixes went in alongside: snapshot/overlay reads are now explicitly
`encoding="utf-8"`, and the ranked table prints through `_safe_print` (cp1252 console +
Gyökeres/Ekitiké/João Pedro = `UnicodeEncodeError` after all the work is done). The CSV
keeps real names.

---

## 2. Prior coverage: 454 / 558 (81.4%)

| Position | Matched | Total | % |
|---|---:|---:|---:|
| GKP | 47 | 60 | 78.3 |
| DEF | 149 | 184 | 81.0 |
| MID | 205 | 246 | 83.3 |
| FWD | 53 | 68 | 77.9 |

By club (sorted ascending — the shape is the sanity check):

| Club | Matched | Club | Matched | Club | Matched |
|---|---:|---|---:|---|---:|
| **Ipswich Town** | 1/27 (3.7%) | Everton | 22/23 (95.7%) | Crystal Palace | 28/29 (96.6%) |
| **Coventry City** | 2/28 (7.1%) | Leeds | 23/24 (95.8%) | Man City | 29/30 (96.7%) |
| **Hull City** | 2/28 (7.1%) | Bournemouth | 24/25 (96.0%) | Fulham | 21/21 (100%) |
| Liverpool | 29/34 (85.3%) | Sunderland | 24/25 (96.0%) | Man Utd | 33/33 (100%) |
| Newcastle | 21/24 (87.5%) | Brentford | 25/26 (96.2%) | Spurs | 36/36 (100%) |
| Chelsea | 27/30 (90.0%) | Arsenal | 27/28 (96.4%) | | |
| Brighton | 29/32 (90.6%) | Nott'm Forest | 25/27 (92.6%) | Aston Villa | 26/28 (92.9%) |

**Sanity check passes.** The three promoted clubs are near-empty exactly as expected (the
handful of hits are players who had PL rows elsewhere last season). Established clubs sit
at 85–100%, with the shortfall being summer signings. A promoted club reading *high* here
would have meant the join was matching the wrong thing.

Using 2024/25 as a secondary fallback would add 22 more players (476/558). Not done: a
two-season-stale prior is a different quality of evidence and should not be silently
blended with a one-season-stale one.

---

## 3. Team model: Dixon-Coles is LIVE

`penaltyblog` was not installed. It is now, in the project venv, via
`pip install penaltyblog --no-deps` per the pyproject comment — plus the transitive deps
its import chain actually needs, which the existing note understates:
`tabulate typing_extensions fsspec networkx lxml plotly matplotlib ipywidgets` (`pip`
itself was missing from the uv-created venv and was restored with `ensurepip`).
`scipy`/`tqdm` were already present.

football-data.co.uk results downloaded through the existing helper
(`python -m fpl_claude.data.football_data fetch 2425 2526`): **760 matches, 2024-08-16 →
2026-05-24**, covering 23 distinct clubs. `TeamModel.fit` succeeds and
`build_team_model()` now returns a real Dixon-Coles model instead of `None`.

Per-club source over the GW1–8 horizon:

| Source | Clubs |
|---|---|
| `dixon_coles` only | Bournemouth, Leeds |
| `dixon_coles+fdr_fallback` | the other 15 established clubs |
| `fdr_fallback` only | **Coventry City, Hull City, Ipswich Town** |

The mixed label is correct and not a defect: an established club's own rating is
Dixon-Coles, but any fixture *against* a promoted club falls back to FDR because
`TeamModel.covers()` requires both sides to clear `MIN_TEAM_MATCHES`. The three promoted
clubs are labelled FDR-fallback, never silently mis-modelled. Confirmed as required.

**But one of the three is right by accident — see defect D6.**

---

## 4. Top 30 by `xpts_horizon`

| # | Player | Team | Pos | £m | xPts(8) | xPts/£m | mins/GW | conf |
|--:|---|---|---|--:|--:|--:|--:|---|
| 1 | Haaland | Man City | FWD | 15.5 | 29.37 | 1.895 | 70.4 | prior |
| 2 | B.Fernandes | Man Utd | MID | 12.0 | 26.28 | 2.190 | 72.3 | prior |
| 3 | Semenyo | Man City | MID | 8.5 | 22.47 | 2.643 | 76.1 | prior |
| 4 | Thiago | Brentford | FWD | 8.0 | 22.38 | 2.797 | 76.1 | prior |
| 5 | Mbeumo | Man Utd | MID | 8.0 | 20.99 | 2.623 | 64.6 | prior |
| 6 | Enzo | Chelsea | MID | 7.0 | 20.71 | 2.959 | 72.3 | prior |
| 7 | Guéhi | Man City | DEF | 6.0 | 20.42 | 3.404 | 72.3 | prior |
| 8 | Raya | Arsenal | GKP | 6.0 | 20.35 | 3.392 | 76.1 | prior |
| 9 | Gabriel | Arsenal | DEF | 8.0 | 20.23 | 2.529 | 62.7 | prior |
| 10 | O'Reilly | Man City | DEF | 6.5 | 19.64 | 3.022 | 60.8 | prior |
| 11 | Gibbs-White | Nott'm Forest | MID | 8.0 | 19.01 | 2.377 | 72.3 | prior |
| 12 | João Pedro | Chelsea | FWD | 7.5 | 18.98 | 2.531 | 64.6 | prior |
| 13 | Watkins | Aston Villa | FWD | 8.0 | 18.77 | 2.347 | 68.5 | prior |
| 14 | Szoboszlai | Liverpool | MID | 7.0 | 18.53 | 2.647 | 74.2 | prior |
| 15 | Rice | Arsenal | MID | 7.5 | 18.40 | 2.453 | 72.3 | prior |
| 16 | Schade | Brentford | MID | 6.0 | 18.23 | 3.039 | 66.5 | prior |
| 17 | Saka | Arsenal | MID | 9.5 | 18.11 | 1.906 | 53.2 | prior |
| 18 | Pickford | Everton | GKP | 5.5 | 17.95 | 3.264 | 78.0 | prior |
| 19 | Gakpo | Liverpool | MID | 7.0 | 17.78 | 2.539 | 66.5 | prior |
| 20 | Rogers | Chelsea | MID | 7.5 | 17.62 | 2.349 | 76.1 | prior |
| 21 | Donnarumma | Man City | GKP | 5.5 | 17.61 | 3.201 | 70.4 | prior |
| 22 | Kelleher | Brentford | GKP | 5.0 | 17.48 | 3.496 | 76.1 | prior |
| 23 | Virgil | Liverpool | DEF | 6.5 | 17.38 | 2.674 | 78.0 | prior |
| 24 | Wirtz | Liverpool | MID | 7.5 | 16.88 | 2.251 | 57.0 | prior |
| 25 | Anderson | Man City | MID | 6.5 | 16.87 | 2.595 | 76.1 | prior |
| 26 | Tavernier | Bournemouth | MID | 6.0 | 16.85 | 2.809 | 64.6 | prior |
| 27 | Verbruggen | Brighton | GKP | 4.5 | 16.82 | 3.738 | 78.0 | prior |
| 28 | Leno | Fulham | GKP | 4.5 | 16.71 | 3.714 | 78.0 | prior |
| 29 | Henderson | Crystal Palace | GKP | 5.0 | 16.65 | 3.329 | 76.1 | prior |
| 30 | Petrović | Bournemouth | GKP | 4.5 | 16.54 | 3.676 | 78.0 | prior |

Broadly plausible at the top. Haaland clear #1, Bruno #2 (penalties + volume), the Arsenal
and Man City defensive blocks well represented. **Seven goalkeepers in the top 30 is the
first thing that should bother you — see D5.**

## Top 30 by `xpts_per_m`

| # | Player | Team | Pos | £m | xPts(8) | xPts/£m |
|--:|---|---|---|--:|--:|--:|
| 1 | **Dubravka** | **Spurs** | **GKP** | **4.0** | **15.46** | **3.866** |
| 2 | Verbruggen | Brighton | GKP | 4.5 | 16.82 | 3.738 |
| 3 | Leno | Fulham | GKP | 4.5 | 16.71 | 3.714 |
| 4 | Petrović | Bournemouth | GKP | 4.5 | 16.54 | 3.676 |
| 5 | Kelleher | Brentford | GKP | 5.0 | 17.48 | 3.496 |
| 6 | Guéhi | Man City | DEF | 6.0 | 20.42 | 3.404 |
| 7 | Kayode | Brentford | DEF | 4.5 | 15.27 | 3.393 |
| 8 | Raya | Arsenal | GKP | 6.0 | 20.35 | 3.392 |
| 9 | Shaw | Man Utd | DEF | 4.5 | 15.11 | 3.357 |
| 10 | Henderson | Crystal Palace | GKP | 5.0 | 16.65 | 3.329 |
| 11 | Roefs | Sunderland | GKP | 5.0 | 16.51 | 3.302 |
| 12 | Sánchez | Chelsea | GKP | 5.0 | 16.44 | 3.287 |
| 13 | N.Williams | Nott'm Forest | DEF | 5.0 | 16.42 | 3.283 |
| 14 | Pickford | Everton | GKP | 5.5 | 17.95 | 3.264 |
| 15 | Donnarumma | Man City | GKP | 5.5 | 17.61 | 3.201 |
| 16 | F.Kadıoğlu | Brighton | DEF | 4.5 | 14.38 | 3.196 |
| 17 | Thiaw | Newcastle | DEF | 5.0 | 15.72 | 3.143 |
| 18 | Mitchell | Crystal Palace | DEF | 4.5 | 14.12 | 3.138 |
| 19 | Lammens | Man Utd | GKP | 5.0 | 15.68 | 3.136 |
| 20 | Martinez | Aston Villa | GKP | 5.0 | 15.27 | 3.055 |
| 21 | Schade | Brentford | MID | 6.0 | 18.23 | 3.039 |
| 22 | O'Reilly | Man City | DEF | 6.5 | 19.64 | 3.022 |
| 23 | Cash | Aston Villa | DEF | 4.5 | 13.53 | 3.008 |
| 24 | Hume | Sunderland | DEF | 4.5 | 13.44 | 2.987 |
| 25 | Enzo | Chelsea | MID | 7.0 | 20.71 | 2.959 |
| 26 | Truffert | Bournemouth | DEF | 5.5 | 15.97 | 2.903 |
| 27 | Vicario | Spurs | GKP | 4.5 | 12.87 | 2.861 |
| 28 | Sels | Nott'm Forest | GKP | 5.0 | 14.30 | 2.859 |
| 29 | Bogle | Leeds | DEF | 4.5 | 12.70 | 2.823 |
| 30 | Tavernier | Bournemouth | MID | 6.0 | 16.85 | 2.809 |

Not one forward, and only two midfielders, in the top 30 by value. That is the D5 problem
again, and the #1 entry is the exact nonsense the brief asked us to look for.

## Top 10 per position

**GKP** Raya 20.35 · Pickford 17.95 · Donnarumma 17.61 · Kelleher 17.48 · Verbruggen 16.82
· Leno 16.71 · Henderson 16.65 · Petrović 16.54 · Roefs 16.51 · Sánchez 16.44

**DEF** Guéhi 20.42 · Gabriel 20.23 · O'Reilly 19.64 · Virgil 17.38 · Matheus N. 16.44 ·
N.Williams 16.42 · Tarkowski 16.24 · Truffert 15.97 · Thiaw 15.72 · Kayode 15.27

**MID** B.Fernandes 26.28 · Semenyo 22.47 · Mbeumo 20.99 · Enzo 20.71 · Gibbs-White 19.01 ·
Szoboszlai 18.53 · Rice 18.40 · Schade 18.23 · Saka 18.11 · Gakpo 17.78

**FWD** Haaland 29.37 · Thiago 22.38 · João Pedro 18.98 · Watkins 18.77 · Gyökeres 16.43 ·
Calvert-Lewin 16.18 · Welbeck 15.24 · Evanilson 14.12 · Mateta 13.81 · Igor Jesus 12.53

---

## 5. Sanity concerns — read this section before trusting any number above

### D1 — Injury flags are priced as 8-gameweek absences, with no return date ✅ *works as designed, wrong for pre-season*

The named checks pass: **Saliba** (`i`, back injury) 0.00, **Ekitiké** (`i`, Achilles,
"expected back 31 Dec") 0.00, **Kulusevski** (`i`, knee) 0.00. 26 players project exactly
zero. Good.

The problem is the mechanism. `minutes.availability()` reads the current `status` /
`chance_of_playing_next_round` and `build_projections` applies that same value to **all
eight** gameweeks. For Ekitiké and Odobert (back 21 Nov) that is right by luck. For the 20
players flagged `d` at 75% it is not: **Šeško** (shin, 8.79), **Kudus** (thigh, 6.54),
**Murillo** (7.66), **Joelinton** (7.03), **Hudson-Odoi** (7.65) all carry a 25% haircut
across all 8 GWs from a knock recorded **27 days before the GW1 deadline**, most of which
will have cleared by kick-off.

`projections.py` already has the right machinery — overlay `duration_gws`, added precisely
because "a one-week doubt priced as an 8-GW absence inflated forced-move EV ~4x" — but it
applies only to *manual* overlays, never to raw API status. Pre-season this systematically
under-rates the entire flagged block. **Mitigation now:** the news sweep must write
`duration_gws` overlays for every flagged player before any squad build. **Real fix:**
parse the return date out of the `news` string and taper availability across the horizon.

### D2 — A thin prior reads as "played and was bad", and nothing flags it 🔴 *worst defect found*

`minutes.priors_from_bootstrap` computes `starts / 38` with **no availability
adjustment**, so a player who missed last season injured is indistinguishable from a squad
filler who was fit and benched. 183 of the 454 matched players have under 900 prior
minutes. The damage where it matters:

| Player | £m | prior mins/starts | xPts(8) | mins/GW | `low_sample` |
|---|--:|---|--:|--:|---|
| **Isak** (Liverpool #9) | 9.0 | 694 / 8 | **5.35** | 20.7 | **False** |
| Havertz | 7.5 | 577 / 7 | 5.81 | 18.8 | False |
| Marmoush | 7.0 | 691 / 8 | 6.02 | 20.7 | False |
| Estêvão | 6.5 | 839 / 12 | 7.81 | 28.3 | False |
| Savinho | 6.5 | 817 / 7 | 5.61 | 18.8 | False |
| Branthwaite | 5.5 | 678 / 7 | 0.92 (GW1) | — | False |
| Colwill | 5.0 | 225 / 2 | 0.45 (GW1) | — | False |

Isak projects 0.67 pts/GW at £9.0m. These are first-choice starters being projected as
bench fodder, and — the part that makes it dangerous — **`low_sample` is `False` for every
one of them**, because `has_prior` is True. The table looks confident. This is strictly
worse than the priorless case, which at least announces itself.

### D3 — Zero-minute prior rows get a full-weight all-zero rates prior 🔴

The extreme form of D2. **50 of the 454 matched players have a prior row with 0 minutes**
(Rashford — on loan abroad, N.Jackson, Kulusevski, Meslier, Tsimikas, Fábio Vieira, …).
Pre-season the current sample is 0, so `rates.blend` gives the prior weight **1.0**, and
because `has_prior=True`, `shrink_newcomers` skips them. Result: **Rashford (£7.0m) carries
`xg90 = xa90 = bonus90 = 0.0`** and his 5.80 xPts is pure appearance + defensive-contribution
points. The bridge refuses to invent zeros for a *missing row*; a *present row of zeros*
walks straight through the same door.

**A blanket minutes threshold is not the fix — I tested it.** I added an opt-in
`--min-prior-minutes` (default **0**, no behaviour change) and ran it at 450:

| Rescued (correctly) | Δ xPts(8) | Promoted (incorrectly) | Δ xPts(8) |
|---|--:|---|--:|
| G.Jesus (Arsenal) | +7.32 | **Arrizabalaga** (Arsenal #2 GK) | **+9.45** |
| Chiesa (Liverpool) | +7.60 | **Trafford** (Man City #2 GK) | **+7.15** |
| Kostoulas (Brighton) | +7.73 | **Benitez** (Palace #2 GK) | **+7.14** |
| Marc Guiu (Chelsea) | +7.29 | **Valdimarsson** (Brentford #2 GK) | **+7.27** |

`low_sample` rises 104 → 187, so the flag does track it. But "few minutes" has two causes —
*injured* and *benched* — and a minutes threshold cannot tell them apart, so it trades D2/D3
for a worse error. It also does not even reach Isak (694 > 450). **The knob ships off and
documented as investigative only; the real fix belongs in the minutes model.**

### D4 — Minutes priors are club-blind: the £4.0m bench keeper the brief warned about 🔴

**Dubravka (Spurs, £4.0m) is #1 in the entire game by `xpts_per_m` (3.866)** and #12 by raw
xPts, **ahead of Vicario (12.87), Spurs' actual first choice**. Cause: he started 35 games
*for Newcastle* last season, and `priors_from_bootstrap` carries that start share to his new
club with no discount. Same mechanism flatters Guéhi (#7 overall), Semenyo (#3) and O'Reilly
(#10) on their Man City moves — those happen to be roughly right, but they are right by
luck, not by model. Every summer transfer needs a minutes overlay before a squad build.

### D5 — Goalkeepers dominate both tables 🟠

Seven GKPs in the top 30 by xPts; the top five by xPts/£m are *all* keepers, and the value
table contains no forwards at all. Pre-season this is structural: a keeper's points
(appearance + saves + clean sheet) are almost entirely recoverable from a prior, whereas
outfield attacking returns get shrunk toward replacement. It may not be *wrong*, but an
optimizer run against this table today would over-buy goalkeepers. **Do not build a squad
off this file until the position-level calibration is checked.**

### D6 — Ipswich falls back to FDR by name mismatch, not by design 🟠

Coventry and Hull genuinely have zero rows in the football-data files. **Ipswich has 38 PL
matches from 2024/25** — but under the name `Ipswich`, while the FPL 2026/27 bootstrap says
`Ipswich Town`, and `data/football_data.py::TO_FPL_NAME` has no mapping for it. So we got
the outcome we wanted (FDR fallback for all three promoted clubs) **by accident**. Had FPL
named them `Ipswich`, they would have been Dixon-Coles-rated off a year-stale relegation
season: `TeamModel.covers()` counts matches and **never checks their age**. Two separate
follow-ups — add the name mappings (a correctness fix), and add a recency guard to
`covers()` (a policy call). Left alone here rather than changing modelling behaviour
silently.

### D7 — 189 players share one identical projection 🟡

All priorless players get `minutes_confidence = "neutral"`, `exp_minutes = 41.70`
(0.5 × 78 + cameo), and the same positional replacement rate, so every Coventry forward
projects **7.53** and every Hull midfielder **6.44**. Correct by design at evidence = 0, and
correctly flagged (`low_sample = True` for 104 players, 18.6% of the game) — but it means
the model has **zero discriminating power over the promoted clubs and every new signing**.
Those picks must come from the news sweep, never from ranking this table.

### D8 — `exp_minutes` is capped at 78 for goalkeepers 🟡 *cosmetic*

`minutes.DEFAULT_START_MINUTES = 78` is an outfield average; a starting keeper plays 90.
Verbruggen/Leno/Petrović read 78.0. No effect on xPts (clean-sheet points gate on `p60`,
not on `exp_minutes`) but the column misleads a human reading the table.

### D9 — `ep_next` benchmark: correlation 0.613 over 532 players 🟢 *informational*

Our mean GW1 xPts 1.61 vs FPL's `ep_next` mean 1.70 — same scale. Where we disagree most
*negatively* we are mostly **right**: Arrizabalaga, Jörgensen, Trafford, Valdimarsson,
Benitez are all backup keepers to whom FPL assigns a flat 2.0–2.6. Where we disagree most
*positively* (Thiago 5.08 vs 2.5, Haaland 6.32 vs 4.0), FPL's pre-season `ep_next` is
essentially a flat prior. **`ep_next` is not a usable calibration target before ~GW3.** The
one genuinely concerning entry on the negative side is Isak (1.09 vs 2.7) — that is D2, not
a benchmark disagreement.

---

## 6. Verdict

The rollover blocker is closed and the run is reproducible. The team model is a real
Dixon-Coles fit on 760 matches, not the FDR crutch. The top of the table is plausible.

**But this file is not yet decision-grade.** D2/D3/D4 all stem from one root cause — *the
minutes prior conflates "did not play" with "cannot play" and ignores club changes* — and
they mis-rank exactly the players a GW1 squad is built around (Isak, Havertz, Marmoush,
Estêvão, Rashford on one side; Dubravka on the other). D1 compounds it across the whole
flagged block. None of these are visible in the `low_sample` column, which is what makes
them dangerous.

Recommended order of work:
1. Minutes prior: divide starts by *available* team games, not 38; add a club-change
   discount. Fixes D2 and D4 at the root.
2. Rates prior: drop the prior when the prior sample is thin **and** the player was
   unavailable — the availability condition is what `--min-prior-minutes` lacks. Fixes D3.
3. Derive `duration_gws` from the `news` return date so injury flags decay over the
   horizon. Fixes D1.
4. Add the football-data name mappings and a recency guard on `TeamModel.covers()`. D6.
5. Only then run the optimizer against this table.

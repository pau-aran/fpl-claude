# Session State — updated 2026-08-20 (GW1 FINAL — iteration 3, the T-35h re-solve)

*Handoff snapshot. Read this first, then `decisions/gw01.md` for the live squad and
`reports/backtest/2025-26/knowledge.md` for the distilled decision knowledge. The build
plan is COMPLETE — `PLAN.md` and `NEXT-STEPS-IMPLEMENTATION.md` were retired 2026-07-26;
what little remains buildable is folded into "Older backlog" below.*

## THE BIG CHANGE: we are no longer in backtest — 2026/27 is open

**The FPL API is reachable from the owner's machine** (`docs/environment.md` has this right).
It is **NOT reachable from a cloud sandbox** — the egress proxy answers 403 to CONNECT for
`fantasy.premierleague.com`, and every FPL news domain (fantasyfootballscout, onefpl, even
wikipedia) is blocked to WebFetch too. `notebooks/provision_from_vaastav.py` is the fallback:
it rebuilds `bootstrap.json` + `fixtures.json` + the team-model results from the vaastav
mirror on raw.githubusercontent.com, which IS allowed. WebSearch works and is the only news
channel there. The 2026/27 game is live with real prices.

| | |
|---|---|
| **GW1 deadline** | **2026-08-21 17:30 UTC** |
| Snapshot | `db/raw/2026-07-25/` — 558 players, 20 teams, 380 fixtures |
| Promoted / relegated | COV, HUL, IPS in; Burnley, West Ham, Wolves out |
| Prices | **FROZEN until the deadline** — no buy-now pressure, no LiveFPL timing edge |
| Ruleset | **VERIFIED** against the live API — optimizer unblocked |
| Squad | `decisions/gw01.md` — **iteration 3, FINAL, ready to enter** (iterations 1-2 archived in the same file) |
| Snapshot (live) | `db/raw/2026-08-20/` — 567 players; team news current to **2026-08-03**, prices frozen |

**Rule changes that matter (verified, `research/2026-27/rules-verification.md`):** the
Assistant Manager chip is GONE; all four chips ×2 (8 total); **BB and TC are playable in
GW1** while WC/FH open at GW2; AFCON bonus free transfers are gone (this invalidates an
assumption in the GW18-24 backtest); BPS internals reworked (don't reuse 2025/26 weights).

**Nine of twenty clubs changed manager** — Maresca (MCI), Iraola (LIV), Alonso (CHE),
De Zerbi (TOT), Glasner (NFO), Sage (CRY), Arbeloa (FUL), Rose (BOU), O'Neil (IPS).
Minutes priors are unreliable across nearly half the league.

## The GW1 thesis (the season's opening edge)

The 2026 World Cup ended **19 July**; mandated rest runs to ~10–12 August, so ~40
FPL-relevant players reach the deadline with ~10 days of training and **no FPL flag**.
It hits **Arsenal and Man City hardest — the two most-templated clubs** — while
**Liverpool are the least damaged big club and own the best GW1–8 fixture run**. The
squad fades the deep runners (Rogers 34.8%, Guéhi 25.3%, O'Reilly 24.8%, Porro 23.9%,
Rice 22.5%) and buys the rested. 55 hand-written overlays in `decisions/overlays/gw01.json`.

**RESOLVED at iteration 3 (2026-08-20).** The Community Shield (ARS v MCI, 16 Aug) was
played and the thesis HELD — Rice, Saka, Guéhi, Zubimendi, Merino and Eze all failed to
start it. Two calls moved against us and were corrected on the evidence: O'Reilly DID start
(0.38 → 0.60) and Gyökeres did NOT (0.78 → 0.55, Havertz played the nine). And the
B.Fernandes fade EXPIRED: on a 5-GW horizon the gap closed from ~0.8-1.0 to **0.064
objective points**, so at 48.6% ownership we now own him rather than pay a 49% EO premium
for a rounding error.

## A3 + A4 shipped (2026-07-25, merged to main), both ADVISORY
*(Update 2026-07-26: A4 has since PASSED its acceptance run — see "Older backlog" below
and `reports/backtest/2025-26/a4-followpath-verdict.md`. The "do not turn it on yet"
below is preserved as written; the edge floor it asked for now exists and is on.)*

Two Opus agents in isolated worktrees, merged and independently re-verified by the
orchestrator. **103 tests green** (was 67); ruff at its 34-finding baseline, zero new.

- **A3 — live `/fpl-review` calibration loop.** `src/fpl_claude/reports/calibration.py` +
  `python -m fpl_claude.reports.calibration --gw N`; append-only log at `notebooks/calibration.md`;
  skill step 5 now runs the command instead of describing manual work. Metrics overall / per
  position / **base-XI vs captain-slot** (the A2 framing), `ep_next` carried side-by-side,
  owned-squad and whole-pool cuts kept separate. **Point-in-time is enforced, not assumed:** a
  projections snapshot dated after the deadline is REFUSED (`PointInTimeError`), never silently
  used, and every rejection is named in the log entry. Verified against the real archive — it
  reproduces the GW24 memo Outcome line exactly (53.68 = base XI 40.96 + captain slot 12.72).
  **Unverified:** `--actuals live` has never made a real API call (injected payload only).
- **A4 — multi-period transfer path.** `src/fpl_claude/optimize/transfer_path.py`: a genuine
  multi-period MILP (own/xi/buy/sell per player per GW, integer FT banking to the rules cap,
  cumulative bank so a GW+1 sale funds a GW+2 buy), pruned to ~70 players, ~9s for 5 GWs. New
  "Transfer path" block in `--propose` prints this-week verdict, the forward path, and what
  banking an FT is worth. **It does NOT decide transfers:** `decide_transfers(follow_path=True)`
  is opt-in, default off, no CLI flag — every committed backtest result is byte-identical.
  **Do not turn it on yet:** its GW25 proposal was a three-move reshape including a
  `Saliba → Raya` churn, exactly the class the manager overlay has vetoed all season, and it has
  zero points-scored evidence. Gate it behind a per-move edge floor and re-run GW17-24 first.
- **Windows console fix** (`src/fpl_claude/console.py`, wired into all 7 CLIs). Found by running
  A3's CLI for real: it computed the entire calibration, then died on `UnicodeEncodeError`
  printing `−`/`≥` under cp1252. `run.py` is the same shape — a GW25 proposal prints `Petrović`
  (U+0107, absent from cp1252), so player names alone would abort a scored gameweek.
- **`docs/environment.md` corrected:** the local workstation is **not** egress-blocked. FPL API,
  football-data and Understat all return 200 from the owner's machine; the 403s were always the
  cloud sandbox's policy. Also records the Windows setup (miniconda + uv venv, one venv per
  worktree) and the ruff-0.16 baseline of 34 pre-existing findings.

## Latest: GW21-24 backtest — the AFCON window CLOSED (this session)

Simulated GW21-24 on the point-in-time pipeline, orchestrated with parallel Opus agents (one
per GW for the point-in-time news replay + consensus; two more for the A1/A2 code tasks).
**The 8-GW AFCON window (GW17-24) is complete: entered at +135, EXIT at +191 — net +56 of
edge built through the season's lowest-average stretch.** Season **1380 vs baseline 1189**,
1 hit all season, captaincy 24/24.
- **GW21 61 v 48 (+13):** ROLL to the 5-FT cap (the returnee window slipped later — both AFCON
  QFs pushed returns back); the refused churn bundle scored 8 vs kept 13+bench; ARS-LIV 0-0
  paid the Liverpool hold.
- **GW22 38 v 40 (−2):** the Semenyo £64m-City-clause risk-class sale → **Bruno G.** over the
  solver's Foden (refused: same rotation class — Foden 45'/1 pt, vindicated same week).
  Deferred both returnee buy-backs on entry-fixture numbers. Tarkowski's 8 stranded on an
  un-named 0.14 bench hair → NEW RULE (list every <0.2 hair).
- **GW23 38 v 44 (−6):** REFUSED the £14 Salah buy-back on written arithmetic (last on our MID
  board; he returned 5); held Konaté through a bereavement + Bruno G. through an ankle knock;
  Brooks→Garner (free). Haaland PRICED 0.70 on a datable exhaustion/UCL flag, captained anyway
  — Pep played him 17' (C returned 2). Priced-variance week, not process error.
- **GW24 64 v 55 (+9):** the window's reshape — {Mateta(out), Szoboszlai(trim)} →
  {**B.Fernandes**, Calvert-Lewin}. Entered B.Fern over Mbeumo on OUR numbers (horizon 24.74 /
  2.60 pts-£m vs 19.82 / 2.36) — right by +8 (deferred Mbeumo 2, B.Fern 10 on debut).

Squad now: Roefs, Dúbravka / Saliba, Timber, Tarkowski, Senesi, Konaté / Rice, Enzo,
**B.Fernandes**, Garner, Bruno G. / Haaland, Thiago, **Calvert-Lewin**. **4 FT, £0.7m** into
GW25. Arsenal triple intact for **DGW26 (confirmed) → TC-Rice queued**; **BGW31 flagged**
(Free Hit/WC). Data self-provisioned via `backtest.fetch`; GW21-24 averages verified.

**Also this session — two code tasks shipped via parallel Opus agents (worktree-isolated,
merged clean):**
- **A1 — chip TIMING advisory** (`src/fpl_claude/optimize/chip_timing.py`, merged `5dc1edb`):
  DGW/BGW detection from fixtures + a chip-EV surface (TC/BB per future GW, nailedness flags,
  half-inventory-aware) + an `advise()` applying the knowledge.md timing rule; wired into
  `run.py --propose` (a "Chip advice" block prints current-GW verdicts + a forward table). It
  surfaced the DGW26 TC-Rice candidate live during the GW21-24 run. Skill updated; tests added.
- **A2 — calibration defect CLOSED** (`reports/backtest/2025-26/calibration.md`, merged
  `248a675`): a full 20-GW decomposition (reproducible via `notebooks/calibration_analysis.py`)
  resolved the [OPEN] as Path A (ranking-correct, EV-reporting-only, NO model change). It
  CORRECTED the old framing — the +4.3/GW residual is in the BASE XI (within noise, t=1.47),
  the captain slot is mean-unbiased (−0.07) and only high-variance. A uniform calibration is a
  proven no-op on picks and the hit-gate; the "scale to league level" term is inoperable
  (predicted-total std 2.96, ~uncorrelated with the slate). FIX: the memo Outcome line now
  splits "predicted = base XI + captain slot (doubled)". 68 tests green, ruff clean.

## Where things stand

- **The PLAN §4 backtest gate PASSED.** Point-in-time replay of 2025/26
  GW1–10 COMPLETE on branch `claude/fpl-data-sources-architecture-5tvqet`:
  **624 pts vs 531 average-manager baseline (+93)**, 1 hit all season,
  captaincy 10/10, no leakage. Beat the field 7/10 weeks; back half (GW6–10)
  +68. On a **top-1% trajectory** (+9.3/GW over average; exact rank an honest
  estimate — top-10k tier totals weren't retrievable). Verdict +
  top-1% assessment in `reports/backtest/2025-26/VERDICT.md`. GW10 executed
  the queued Ekitiké→Mateta (Mateta 9 vs Ekitiké 2, +7) + Ballard→Konaté,
  Haaland (C) 26 → 75 vs avg 65.
- **Mid-run model fix shipped:** newcomer confidence haircut
  (`shrink_newcomers`, GW8+). Three defects found and queued for the LIVE
  pipeline (VERDICT.md §Defects): level-calibration under-prediction,
  bench-order fixture-softness, suspension verification.
- **New: `src/fpl_claude/backtest/`** — SeasonStore (vaastav point-in-time
  reconstruction), simulator (real FPL mechanics: sell prices, FT banking,
  autosubs, hit gate), per-GW CLI with persisted state, availability-proxy +
  researched news overlays (duration-scoped), decision memos.
- **The decision architecture matured during the run** (owner-steered):
  models PROPOSE, the manager DISPOSES — `--propose` / `--decision`
  (lock/ban/captain/cap + written reasoning), a standing multi-week
  transfer-path plan (`plan.md`, hits must fit the plan, not just the EV
  gate), community consensus as a weekly input (`consensus/gwNN.md`), and
  per-week reviews + a living `knowledge.md` (DONE/OPEN/WATCH).
- **Five pipeline defects found and fixed via the weekly review loop** (all
  live-pipeline relevant): tiny-sample per-90 explosion, Dixon-Coles trusting
  1-match teams, DC phantom-zero prior, package-EV hit gate (now marginal
  NET per hit), overlay-horizon poisoning (now duration_gws). 35 tests, ruff
  clean.
- **Sources refined:** `docs/fpl-sources-reference.md` (field-tested,
  FPL-only, incl. FBref) + 17 vetted X accounts in `config/sources.yaml`.
- **Network reality unchanged** (see `docs/environment.md`): FPL API/news
  domains still blocked; GitHub + WebSearch carry everything above.

## GW1 iteration 3 — what was decided (2026-08-20, T-35h)

**Squad (£100.0m, bank £0.0m, 4-4-2, Haaland C / B.Fernandes V, no chip):**
Kelleher, Heaton / Tarkowski, **Gvardiol**, **Calafiori**, Thiaw, O'Shea /
**B.Fernandes**, Semenyo, Mbeumo, Schade, Crooks / Haaland, Calvert-Lewin, Neave.
Predicted GW1 XI **52.39** (base 46.19 + captain 6.20 doubled); 5-GW objective **190.658**.

- **Horizon 5, not 8** (owner instruction). On identical data the two horizons share only
  9 of 15: the 5-GW view buys **B.Fernandes** (Man Utd's HUL-away + IPS-home opener is the
  softest pair in the league and it expires) and drops Gabriel, João Pedro and Wirtz. Mean
  effect is small — the club-level H5/H8 ratio spans 0.747-0.777 around a neutral 0.764 —
  so the horizon does not re-rank the league, it flips players across the budget knife-edge.
- **Spend was swept, not assumed** (owner instruction). New `optimize(budget=...)` /
  `run_live --max-spend` + `notebooks/gw01_spend_frontier.py`. Verdict: **spend the £100.0m.**
  The frontier is flat-free at ~1.05 decayed 5-GW points per £1.0m banked with no knee, the
  XI-only column agrees (so it is not a bench artefact), and locking this XI and re-solving
  for the cheapest legal 15 returns **£100.0m exactly, infeasible at £99.5m** — the bench is
  already at FPL's price floor (4.0+4.0+4.5+4.5).
- **Overlay iteration 3**: `decisions/overlays/gw01-it3.json`, 63 entries (56 carried, 14
  revised, 7 new), built by `notebooks/build_overlay_gw01_it3.py`. Biggest calls: Guéhi
  0.50→0.30 (against our own model, which had him the best defender in the game), Gvardiol
  NEW 0.85, Calafiori NEW 0.80, Doku 0.00 (calf in the Shield, **no FPL flag**), Lacroix
  0.15→0.80 (his Chelsea move completed, so the July fade had expired).
- **Reproduce:** `python notebooks/provision_from_vaastav.py --out-date 2026-08-20` then
  `python -m fpl_claude.models.projections --from-snapshot 2026-08-20 --prior-season-csv
  db/vaastav/2025-26/players_raw.csv --horizon 5 --overlays decisions/overlays/gw01-it3.json`.

## What the next session should do

1. **T-2h final check (2026-08-21, ~15:30 UTC).** The two lines that would move the squad
   are named in `decisions/gw01.md` §8. If B.Fernandes is out or rested, **V4 is already
   solved** (−0.06 objective): Gabriel, Wirtz, Thiago, Obi, McConnell in for Bruno, Schade,
   Calvert-Lewin, O'Shea, Neave.
2. **Post-GW1 review** (`/fpl-review`, ~24 Aug). This is also the **first honest chance to
   verify A3's `--actuals live` path**, which has still never made a real API call — and it
   cannot be verified from a cloud sandbox, only from the owner's machine.
3. **GW2 is the Liverpool entry** per the standing plan: they own the best GW1-5 run
   (summed FDR 13) but GW1 is Newcastle away, their worst. Targets in order: Wirtz, Gakpo,
   Virgil. Man Utd's opener expires after GW2 — reassess Bruno/Mbeumo then.
4. **Two model defects still open** in `research/2026-27/model-fixes.md`: D1 (injury flags
   priced as horizon-long absences) and D2/D3 (thin/zero-minute priors). D2 has a live cost
   now: **Isak** projects 11.69 over five gameweeks off a 694-minute prior while being
   Liverpool's predicted nine and penalty taker. He is unpriced, not rejected.
5. **`/fpl-team-week-report` has still never run** — first-class deliverable per CLAUDE.md.
6. **D6 note:** the recency guard works. Ipswich clears MIN_TEAM_MATCHES on 38 matches from
   2024/25 and is correctly rejected on MIN_RECENT_MATCHES, so all three promoted clubs sit
   on the FDR fallback. Also worth knowing: a shared per-season download cache silently fed
   the team model two copies of one season on the first provisioning attempt — the bug is
   fixed and documented in `provision_from_vaastav.py`.

### Older backlog (pre-season) — CLEARED 2026-07-26

The build plan is complete; `PLAN.md` and `NEXT-STEPS-IMPLEMENTATION.md` were retired
(deleted) once every A item closed. For the record and for what little remains:
1. ~~**Prove A4 before trusting it**~~ — **DONE, PASS** (2026-07-26). The per-move edge floor
   (`MOVE_EDGE_FLOOR`, 0.5 decayed pts) shipped, and GW17-24 was re-simulated with
   `follow_path=True` from a reconstructed, cross-checked GW17 entry state: **floored path
   438 vs the hand-written 439** (+59 vs the field's +60), zero hits; unfloored churned every
   week for 432, so the floor's value is measured at +6. A4 is now an evidence-backed
   advisory; `follow_path` stays opt-in and the manager keeps the veto. Full verdict and
   caveats: `reports/backtest/2025-26/a4-followpath-verdict.md`; runner:
   `notebooks/a4_followpath_gw17_24.py`.
2. **Optional backtest continuation** — GW25-26 would fire the FIRST live chip in-sim
   (**TC-Rice on the confirmed Arsenal DGW26**), and GW31 the BGW (a Free Hit/WC trigger).
   Also the natural second window for A4 plan-stability evidence.
3. **A5 (data-source clients)** — the one unstarted A item; add breadth as the season demands.
4. **Automation arming (Phase 5)** — scheduled sessions (daily refresh/news, Monday reports,
   T-48h/24h/2h deadline runs, post-GW review). Everything it depends on now exists.
5. **Verify A3's live-actuals path** — `--actuals live` has still never made a real API call;
   GW1 completing (~22 Aug) is the first honest chance.

## Backtest scoreboard (2025/26 replay)

| GW | Ours | Avg | Note |
|---|---|---|---|
| 1 | 84 | 54 | Overlay-informed build; Salah C |
| 2 | 44 | 51 | Bad hit (pre-gate) — the week that built the hit policy |
| 3 | 54 | 48 | First manager veto (held Palmer) |
| 4 | 61 | 63 | Held Saliba; forced move only |
| 5 | 40 | 42 | Plan discipline: rolled FT for Haaland window |
| 6 | 55 | 46 | Haaland lands on plan + 67% consensus; captained |
| 7 | 71 | 60 | Rolled FT (2 banked); Haaland C g+a; refused plan-conflict −4; Semenyo 18 |
| 8 | 82 | 56 | Triple-out (Palmer/Gud/Brooks); 2 FT no hit; faded Saka→Fernandes; Haaland C 26 |
| 9 | 58 | 46 | Rolled FT (deferred Ekitiké→Mateta); Haaland C blank; Mbeumo 15, Szoboszlai 10 |
| 10 | 75 | 65 | Ekitiké→Mateta + Ballard→Konaté; Haaland C 26; Mateta 9 |
| **Σ1-10** | **624** | **531** | **+93; hits: 1; captaincy 10/10 — GATE PASSED** |
| 11 | 34 | 38 | −4 variance (2 in-squad pen misses); rolled FT; 7th churn veto |
| 12 | 42 | 39 | Semenyo→Enzo (11); banned injured Gabriel; Muñoz 14 |
| 13 | 44 | 35 | Scarlett→Thiago (13 debut) + Raya→Roefs; bench-order −8 |
| 14 | 69 | 58 | 4 one-week absences rolled; Haaland C drought ended 28 |
| 15 | 56 | 49 | Rolled to 3 FT; held Mbeumo (8); Fernandes 18 |
| 16 | 72 | 60 | Rolled to 4 FT; held Mbeumo send-off; Haaland C 26; autosubs +11 |
| 17 | 70 | 66 | AFCON reshape: Mbeumo→Rice (11) + Muñoz→Tarkowski; Haaland C 32 |
| 18 | 43 | 44 | Bruno OUT→Semenyo (9); refused Mbeumo AFCON trap; autosubs covered 2 blanks |
| 19 | 62 | 40 | Calafiori OUT→Timber (9); Rice benched; refused buy-back-injured-Bruno |
| 20 | 63 | 42 | ROLL→4 FT; held Enzo thru MCI-A (11); Rice back (17) |
| 21 | 61 | 48 | ROLL to the 5-FT cap; refused the churn bundle; ARS-LIV 0-0 paid the bloc hold |
| 22 | 38 | 40 | Semenyo £64m clause → Bruno G. (over Foden); deferred returnees; Tarkowski 8 benched |
| 23 | 38 | 44 | Refused £14 Salah; held Konaté (bereavement)+Bruno G. (ankle); Haaland priced 0.70, 17' |
| 24 | 64 | 55 | Window close: Szob→B.Fernandes (10 deb, over Mbeumo) + Mateta(out)→CL; base XI +20.7 |
| **Σ1-24** | **1380** | **1189** | **+191; hits: 1; captaincy 24/24 — AFCON window (GW17-24) net +56** |

## Recent session log

- **2026-08-20 (GW1 ITERATION 3 — the deadline re-solve, 5-GW horizon):** branch
  `claude/gw1-team-threadhole-redo-pc5rqd`. Owner instruction: redo the GW1 squad on a
  **5-gameweek** horizon and stop assuming the full £100.0m. Both were done as measurements,
  not assertions. **Horizon:** on identical data the 5-GW and 8-GW squads share 9 of 15; the
  5-GW view buys **B.Fernandes** (Man Utd's soft, expiring opener) and drops Gabriel, João
  Pedro and Wirtz — while the club-level H5/H8 ratio only spans 0.747-0.777, so the effect is
  marginal, not a re-ranking. **Spend:** shipped `optimize(budget=...)` +
  `run_live --max-spend` + `notebooks/gw01_spend_frontier.py`, swept £100.0m→£95.0m, and the
  answer is spend it — ~1.05 decayed points per £1.0m banked with no knee, and locking the XI
  makes £99.5m INFEASIBLE because the bench is already at FPL's price floor. **News:** the
  Community Shield gate iteration 2 set was played and the World Cup thesis HELD (Rice, Saka,
  Guéhi, Zubimendi, Merino, Eze all did not start); two calls were corrected against us
  (O'Reilly started, Gyökeres did not); Doku picked up a calf injury *in* that match and
  carries **no FPL flag**. 63-entry overlay iteration 3, each with a written reason.
  **Environment:** the FPL API and every FPL news domain are egress-blocked in the cloud
  sandbox — built `notebooks/provision_from_vaastav.py` (mirror → bootstrap/fixtures +
  football-data-shaped results), validated by reproducing the committed 8-GW top-30 ordering
  to within 2-4%. Two defects caught in my own work rather than shipped: a shared download
  cache fed the team model two copies of one season (which let relegated Ipswich clear the
  recency guard), and the mirror's `players_raw.csv` carries LAST season's stats against
  CURRENT ids, so every accumulated column is zeroed and the prior supplied separately.
  **200 tests green** (2 new for the spend cap); ruff unchanged — 23 findings introduced and
  all 23 fixed before commit.
- **2026-07-26 (THE SEASON OPENED — first live squad):** branch
  `claude/gw1-2026-27-squad-build`. Found the **FPL API reachable for the first time** and
  pulled the live 2026/27 game (558 players, real prices, GW1 deadline 2026-08-21).
  Orchestrated **seven parallel Opus agents** (transfer window, WC26 fitness, team/manager
  landscape, rules verification, market template, season-bridge + projections, live CLI)
  while running the manager loop directly. Shipped: verified ruleset (optimizer unblocked),
  `data/season_bridge.py` (cross-season `code` remapping — a naive id-join would have
  attached the wrong player's history to every row), `optimize/run_live.py` (the live
  deadline CLI with bench-hair, blind-spot, club-cap and hit-gate guards), Dixon-Coles
  live on 760 real matches, and **`decisions/gw01.md` — the season's opening squad**.
  Three defects caught and corrected rather than shipped: the market leg recommended
  **Ekitiké at 0.2% ownership** off last season's points-per-minute while he has a ruptured
  Achilles (retracted in place, with the violated rule restated); the projections table was
  declared unsafe to optimise against by its own author and **three prior-layer defects were
  fixed** (zero-minute prior rows weighted as measured, thin priors flagged confident,
  club-change blind spot — Dubravka ranked #1 in the game on 35 Newcastle starts); and a
  `Path.write_text` encoding bug that crashed memo-writing on Windows **after** advancing
  backtest state. Backtest regression replayed: **GW1 reproduces exactly at 84**, Σ1-6 366
  vs the original 338 (directional only — later weeks replay fixed decisions against a
  changed model). 112 tests green. **Process note: concurrent sessions were checking out
  branches in the same working tree mid-run**, scattering two commits onto foreign branches;
  recovered by cherry-pick, and all pushes now use an explicit refspec.
- **2026-07-25 (code session — A3 + A4):** branch `claude/a3-a4-calibration-multiperiod`. Two
  Opus agents in isolated worktrees with hard file-ownership boundaries (A3: `reports/`,
  `notebooks/`, the review skill; A4: `optimize/`, `backtest/`, the plan/fixture skills), merged
  clean with no conflicts. Orchestrator re-verified both rather than taking the reports at face
  value: ran A3's CLI against the committed `gw24_players.csv` (reproduced the memo line exactly,
  and the point-in-time guard did reject a post-deadline snapshot) and ran A4's `--propose` for
  GW25 against real vaastav data (9.2s, output as reported). That verification is what surfaced
  the **cp1252 console defect** — A3's CLI finished its work and then crashed on the way out —
  fixed repo-wide in `console.py`. 67 → **103 tests**, ruff unchanged. Also corrected the
  long-standing "network blocked" premise: it is the sandbox's, not this machine's.
  **Both features are ADVISORY** — `follow_path` default off, live actuals unverified.
  Housekeeping note: a parallel session on `main` deleted `NEXT-STEPS.md` and created the
  `claude/a6-*`, `claude/a7-*` and `claude/gw1-*` branches/worktrees; left untouched here.

- **2026-07-24 (GW21-24 session — the AFCON window CLOSED + A1/A2 shipped):** branch
  `claude/simulate-gw-18-19-20-rff52m` (PR #4). Orchestrated parallel Opus agents (per-GW
  point-in-time news/consensus researchers + two worktree-isolated code agents) while running
  the manager decision loop myself. **Closed the 8-GW AFCON window (GW17-24) at +191 — net +56
  of edge** through the season's lowest-average stretch; GW21-24 went 61/38/38/64 (v 48/40/44/55).
  The window's spine: rode the loaded runs on banked FTs (never a chip — the counterfactual
  proved FT-only right), sold Semenyo on his £64m City clause (GW22), refused the £14 Salah
  buy-back on written arithmetic (GW23), and entered B.Fernandes over Mbeumo on horizon/value
  (GW24, right by +8). Two −6 weeks (GW22-23) were priced variance (a forecast Haaland 17'
  rotation, a bloc CS bet that failed), recovered in one at GW24 (base XI +20.7). Shipped
  alongside: **A1** (chip-timing advisory — `optimize/chip_timing.py`, `--propose` chip block,
  merged `5dc1edb`; it surfaced the TC-Rice DGW26 candidate live) and **A2** (calibration
  defect closed Path A — `calibration.md` + the memo base/captain split, merged `248a675`).
  68 tests green, ruff clean. Two NEW process rules from the run (list every <0.2 bench hair;
  pure-CS duel-name caution) + one [WATCH] (widen the DEF-CS hair to ~0.3). All memos/reviews/
  consensus/overlays committed; STATE/NEXT-STEPS-IMPLEMENTATION/plan/knowledge/baseline updated.
- **2026-07-24 (GW18-20 session — the AFCON+festive trough):** branch
  `claude/simulate-gw-18-19-20-rff52m`. Ran the next three backtest GWs (26 Dec–3 Jan, the
  three-in-nine festive rounds stacked on AFCON) on the point-in-time pipeline. **168 v 126
  (+42); season 1179, edge +177 (season high); 0 hits, captaincy 20/20.** GW18: B.Fernandes
  OUT (hamstring, sourced to Amorim's Boxing-Day presser) → Semenyo (value cover, Ghana not
  at AFCON, 9 debut), banked 2 FT, refused the model's Mateta→Mbeumo AFCON buy-back trap;
  autosubs covered two UNFORECASTABLE blanks (Calafiori's warm-up injury struck ~20h after
  the deadline — a genuine point-in-time miss for the field too — plus Szoboszlai) — 43 v 44.
  GW19: Calafiori OUT (muscle ~month, now public) → Timber (9 debut), benched Rice (1-wk
  knee, held-not-sold), refused the model's buy-back-AND-captain-injured-Bruno line — 62 v 40
  (+22). GW20: ROLL (0 transfers → 4 FT banked toward the returnee window), held Enzo through
  MCI(A)5 (11) + Rice returned (17), both "hold" rules vindicated same week — 63 v 42 (+21).
  Haaland (C) blanked all three (2/2/2) — captain-slot variance, borne by the field. One
  process miss logged: GW19 Konaté (duel-named CS bet) benched on a 0.06 hair (7 stranded,
  ~−4) — `force_start` lever not pulled → new standing rule in knowledge.md/plan.md. Sources
  web-verified (Bruno/Calafiori/Rice injuries, AFCON/Ghana). Data self-provisioned via
  `backtest.fetch`; GW18-20 averages (44/40/42) matched the prior look-ahead.
- **2026-07-23 (GW17 session — the AFCON reshape):** branch
  `claude/next-sim-8gw-decision-tree-j7wl1n`. Ran the next backtest GW (GW17), the
  first round of the AFCON exodus, and rebuilt the standing decision tree for the full
  8-GW AFCON window (GW18-24). GW17: executed the reshape on 2 of 4 banked FT, no hit —
  **Mbeumo→Rice** (the Cameroon/AFCON sale, reinvested into the cheapest rider of
  Arsenal's elite run at £7.1; 11 on debut) + **Muñoz→Tarkowski** (the confirmed
  multi-week injury sale, banking £0.5 to a £1.2 buffer). Locked Saliba (refused the
  11th Saliba→Timber churn), banked 2 FT (→3 for GW18). Captain Haaland at home to West
  Ham → 32 (17/17 adherence). **GW 70 vs avg 66 (+4); season 1011 — past 1000, edge
  +135 (season high).** plan.md's "Active path" is now an 8-GW week-by-week tree (ride
  the loaded Arsenal/City/Liverpool runs, bank FT/£ through the low-average trough,
  reassess at the returnee window GW22-23). Two live threads: the fixture-blind
  bench-order defect hit a 3rd time (Saliba's 6 benched behind Tarkowski, ~−3) and
  B.Fernandes subbed 45' (fitness watch for GW18). Data self-provisioned via
  `backtest.fetch` (vaastav); official GW17-24 averages fetched into baseline.md.
- **2026-07-22 (GW7 session):** new branch
  `claude/fpl-data-sources-architecture-5tvqet`. Folded owner data-source
  feedback into the sources reference/`sources.yaml` (official API +
  Understat = core ~90%; FBref advanced feed dead Jan 2026 → xgstat.com;
  LiveFPL = price-prediction standard; Reddit/PRAW; X-API caveat + RSS/
  Discord relay path) and bench policy. Added the purist positional-duel
  lens (owner directive) to knowledge.md + the plan-gameweek skill. Ran GW7:
  rolled the FT, captained Haaland (g+a) → 71 vs avg 60; refused the −4
  (Saliba→Timber + Palmer→Enzo) as plan-conflicting — process PASS though it
  would have won by ~3 on a Timber CB goal. Season 409 (+45). Overlay agent
  failed on session limit; overlay built directly. STOP for owner verify.
- **2026-07-22 (earlier this day):** built the season-replay backtest harness;
  ran GW1–6 with parallel agents (news replay, reviews, consensus); shipped
  5 model/policy fixes; added manager decision layer, plan.md, fixture
  planner skill, sources reference, X account vetting. Merged to main after
  GW6 per owner instruction.
- **2026-07-22 (earlier):** project state verified; SessionStart hook;
  environment doc; PR #1/#2.

*Keep this file current: overwrite "Where things stand"/"next session" each
session; append to the log.*

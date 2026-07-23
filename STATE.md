# Session State — updated 2026-07-23 (backtest session — GW17 done, AFCON reshape)

*Handoff snapshot. Read this first, then `NEXT-STEPS.md` for the roadmap and
`reports/backtest/2025-26/knowledge.md` for the distilled decision knowledge.
GW1 deadline ≈ mid-August 2026 (~3 weeks out).*

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

## What the next session should do

1. **Backtest gate is DONE (PASSED, +93).** Next real work is the LIVE
   pipeline: implement the three queued [OPEN]s (level calibration,
   bench-order fixture softness, suspension verification — see VERDICT.md /
   knowledge.md) so they're in place before GW1 2026/27. These are the
   highest-leverage remaining quality gains toward a verified top-1%.
2. **Final gate verdict + report** (10-GW total vs 531 baseline; process
   audit from `reviews/`), fold into NEXT-STEPS §2 and drop the "ungated"
   label if passed.
3. Then the pre-GW1-2026/27 items in NEXT-STEPS §§1,3 (network allowlist
   re-test, season-launch rules verification).

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
| **Σ** | **624** | **531** | **+93; hits: 1; captaincy 10/10 — GATE PASSED** |

## Recent session log

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

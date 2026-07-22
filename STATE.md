# Session State — updated 2026-07-22 (backtest session — GW7 done)

*Handoff snapshot. Read this first, then `NEXT-STEPS.md` for the roadmap and
`reports/backtest/2025-26/knowledge.md` for the distilled decision knowledge.
GW1 deadline ≈ mid-August 2026 (~3 weeks out).*

## Where things stand

- **The PLAN §4 backtest gate is RUNNING and passing.** Point-in-time replay
  of 2025/26 GW1–10; now through **GW7 on branch
  `claude/fpl-data-sources-architecture-5tvqet`**: **409 pts vs 364
  average-manager baseline (+45)**, no leakage (stats through GW n−1 only,
  prices at GW n, prior season via cross-season `code`). GW7 rolled the FT
  (2 FT banked for GW8), captained Haaland (goal+assist) → 71 vs official
  avg 60 (+11); refused the optimizer's −4 as plan-conflicting.
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

1. **Finish the backtest**: GW8–10 (same weekly cadence: overlay agent →
   propose → manager decision vs plan.md → run → reviewer agent). State
   lives in `reports/backtest/2025-26/state.json` (resume with
   `python -m fpl_claude.backtest.run --gw 8`; data via
   `python -m fpl_claude.backtest.fetch --dest <scratch>`). GW8 is the
   post-break decision window: Palmer's return, Isak's confirmed starts
   (Ekitiké→Isak branch), any break knocks — 2 FT, no hit budgeted. See
   plan.md "Active path — the GW8 decision window".
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
| **Σ** | **409** | **364** | **+45; hits: 1; captaincy rule 7/7** |

## Recent session log

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

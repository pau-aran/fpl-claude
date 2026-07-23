# Session State — updated 2026-07-23 (backtest session — GW17 done)

*Handoff snapshot. Read this first, then `NEXT-STEPS.md` for the roadmap and
`reports/backtest/2025-26/knowledge.md` for the distilled decision knowledge.
GW1 2026/27 deadline ≈ mid-August 2026 (~3 weeks out).*

## Where things stand

- **The 2025/26 season-replay backtest is now through GW17.** Point-in-time,
  strictly no leakage: **1001 pts vs the 876 average-manager baseline (+125)** —
  the **1000-point milestone crossed**. 1 hit all season, captaincy 17/17.
  Artifacts in `reports/backtest/2025-26/`; per-GW memos `gwNN.md`, reviews
  `reviews/gwNN.md`, community-consensus reconstructions `consensus/gwNN.md`,
  news overlays `overlays/gwNN.json`, manager decisions `decisions_gwNN.json`,
  the standing transfer plan `plan.md`, distilled `knowledge.md`, rolling
  `state.json`.
- **GW17 was the AFCON reshape** (the exodus planned since GW12). Two forced
  moves, no hit, 2 FT banked: **Mbeumo (Cameroon, AFCON) → Foden** (form + soft
  run + 33%-owned differential) and **Muñoz (knee surgery, 4-6wk) → Keane**
  (£4.6 Everton CB, restores the £0.3 buffer). Refused the optimizer's Gakpo buy
  (injured — the archive hides it), Brooks→Dewsbury-Hall, and the 11th
  Saliba→Timber. Captain Haaland (WHU home) returned 16 (3rd in four weeks).
  GW **60 vs avg 66 (−6)** — first below-average week since GW11; the −6 was a
  quiet non-Haaland attack PLUS the [OPEN] fixture-blind bench order leaking ~5
  (benched Saliba's CS out-scored the started Konaté's blank).
- **The bench-order [OPEN] has now cost points three times** (GW10 −3, GW13 −8,
  GW17 −5) — the biggest recurring leak, escalated for the live pipeline
  (knowledge.md). Interim: manual bench-order overlay (start the softer-fixture
  DEF) each GW.
- **The decision architecture** (owner-steered) is stable: models PROPOSE via the
  MILP, the manager DISPOSES via `--decision` (lock/ban/captain/max_transfers +
  written reasoning); a standing multi-week `plan.md` (hits must fit the plan,
  not just the EV gate); community consensus as a weekly input; per-week reviews
  + the living `knowledge.md`; the purist positional-duel lens as the creative
  overlay.
- **Data:** `python -m fpl_claude.backtest.fetch --dest db/vaastav` self-provisions
  the vaastav archive (GitHub raw reachable; FPL API/news domains still blocked —
  see `docs/environment.md`). WebSearch carries point-in-time news reconstruction.

## What the next session should do

1. **Continue the replay: GW18** (`@next-sim`). Opens with **3 FT, £0.3m bank**,
   season 1001 (+125). Pre-committed watch: apply the manual bench-order overlay
   (the GW17 leak); hold Foden through his one-week blank; AFCON returnees window
   is GW20-21 (banked FTs). Full cycle: consensus reconstruction → news overlay →
   `--propose` → manager decision → run → review; update plan.md/baseline.md/this
   file. GW18 official avg = 44 (baseline look-ahead, already fetched).
2. **Highest-leverage code fix before GW1 2026/27:** the bench-order defect
   (weight FDR/CS-probability in XI ordering, or a first-class manager
   bench-order override). Three quantified leaks now justify it over the other
   [OPEN]s.
3. The pre-GW1-2026/27 items in NEXT-STEPS §§1,3 (network allowlist re-test,
   season-launch rules verification) remain the real-season gating work.

## Backtest scoreboard (2025/26 replay)

| GW | Ours | Avg | Note |
|---|---|---|---|
| 1–10 | 624 | 531 | GATE PASSED (+93); 1 hit; captaincy 10/10 |
| 11 | 34 | 38 | Haaland pen miss; churn veto (7th) vindicated |
| 12 | 42 | 39 | Semenyo→Enzo (injury+AFCON); banned injured Gabriel |
| 13 | 44 | 35 | Scarlett→Thiago + Raya→Roefs value reshape |
| 14 | 69 | 58 | Rolled through 4 absences; Haaland C 28 |
| 15 | 56 | 49 | Rolled to 3 FT; held Mbeumo pre-AFCON |
| 16 | 72 | 60 | Saliba return covers Calafiori ban; Haaland C 26 |
| 17 | 60 | 66 | AFCON reshape (Mbeumo→Foden, Muñoz→Keane); Haaland C 16; bench-order −5 |
| **Σ** | **1001** | **876** | **+125; hits: 1; captaincy 17/17** |

## Recent session log

- **2026-07-23 (GW17 session, `@next-sim`):** ran the AFCON reshape. Resolved the
  GW16 Muñoz [WATCH] via news sweep (knee surgery, 4-6wk → sell); confirmed Mbeumo
  out (AFCON) and Foden as the form/fixture/differential cover; caught Gakpo's knock
  the archive hides (refused the optimizer's Muñoz→Gakpo). Banked 2 FT for the
  returnee window. GW 60 vs avg 66 (−6, first below-avg since GW11); season 1001
  (+125), 1000 crossed. Escalated the bench-order [OPEN] (3rd leak, −5 this week).
- **Earlier (GW11–16):** point-in-time replay continued on the checkpoint branch;
  merged penalty/set-piece signal + `ep_next` benchmark from the repo-analysis branch.
  Season ran 658→941 across GW11-16 with the disciplined-roll pattern.
- **2026-07-22:** built the season-replay harness (GW1–10 gate, +93); shipped 6
  model/policy fixes; added the manager decision layer, plan.md, fixture planner,
  sources reference, X-account vetting. See git log for the full arc.

*Keep this file current: overwrite "Where things stand"/"next session" each
session; append to the log.*

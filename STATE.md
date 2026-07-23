# Session State — updated 2026-07-23 (backtest session — GW20 done)

*Handoff snapshot. Read this first, then `NEXT-STEPS.md` for the roadmap and
`reports/backtest/2025-26/knowledge.md` for the distilled decision knowledge.
GW1 2026/27 deadline ≈ mid-August 2026 (~3 weeks out).*

## Where things stand

- **The 2025/26 season-replay backtest is now through GW20.** Point-in-time,
  strictly no leakage: **1140 pts vs the 1002 average-manager baseline (+138 — a
  season-high edge)**. 1 hit all season, captaincy 20/20 adherence. Artifacts in
  `reports/backtest/2025-26/`: per-GW memos `gwNN.md`, reviews `reviews/gwNN.md`,
  consensus reconstructions `consensus/gwNN.md`, news overlays `overlays/gwNN.json`,
  manager decisions `decisions_gwNN.json`, standing plan `plan.md`, distilled
  `knowledge.md`, rolling `state.json`.
- **GW18-20 navigated the festive/AFCON cascade** (three forced injuries + Boxing-Day
  congestion): GW18 B.Fernandes (hamstring) → Cunha, **35 vs 44 (−9)** on a cold slate;
  GW19 ROLL (refused a churn bundle incl. the injured Rice), **51 vs 40 (+11)**; GW20 the
  defensive reshape Calafiori→Tarkowski + Szoboszlai→Semenyo, **53 vs 42 (+11)** with
  Thiago 17 / Enzo 11 / Cunha 9 carrying a THIRD straight Haaland captain blank.
- **NEW: the bench-order [OPEN] is FIXED and shipped (GW18).** `reselect_xi`
  (backtest/simulate.py) now fields the XI/captain/bench on the current GW's
  `xpts_gw{gw}` (fixture-aware), not the season horizon the squad MILP uses — the
  transfer logic is untouched, forward-only, 38 tests. Root cause was `optimize()` using
  one horizon score for both squad AND lineup. Three clean weeks since (banned/doubtful
  players correctly benched). This was the #1 flagged defect since GW10.
- **NEW doctrine: the Manager's Read is a co-equal voice** (owner directive 2026-07-23,
  live from GW18). Write the human read (team trajectory / eye-test, captaincy bravery,
  bench order) BEFORE reading the solve; it may override the model on those weak axes
  against MODEST EV, but plan-fit + the minutes gate stay sacred and LARGE EV gaps go to
  the model. Every deviation is graded weekly. First test cases logged (GW19 Cunha-captain
  veto correct; GW20 held EV over a Bournemouth-trajectory hunch when the gap was ~5 pts).
- **Data:** `python -m fpl_claude.backtest.fetch --dest db/vaastav` self-provisions the
  vaastav archive (GitHub raw reachable; FPL API/news domains still blocked). WebSearch
  carries point-in-time news reconstruction (GW18-20 used parallel research agents).

## What the next session should do

1. **Continue the replay: GW21** (`@next-sim`). Opens **3 FT, £0.3m bank**, season 1140
   (+138). GW21 official avg = 48 (baseline look-ahead). Full cycle: Manager's Read first
   → consensus/news overlay → `--propose` → decision → run → review; update the docs.
   Pre-committed watch: the **AFCON-returnee window opens (~GW21-23)** — plan re-buys on
   CONFIRMED exits, not projections; monitor Semenyo (the EV-over-Read buy) and the
   Haaland captain drought (shield holds — squad depth is covering it).
2. The bench-order fix is DONE; the remaining live-pipeline [OPEN]s (level calibration,
   suspension verification — VERDICT.md) are lower-leverage. Captain-slot variance is a
   [MONITOR], not a fixable defect (a recency switch would have missed GW14/16/17 hauls).
3. Pre-GW1-2026/27: NEXT-STEPS §§1,3 (network allowlist re-test, season-launch rules
   verification) remain the real-season gating work.

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
| 17 | 60 | 66 | AFCON reshape (Mbeumo→Foden, Muñoz→Keane); bench-order −5 |
| 18 | 35 | 44 | Bruno→Cunha (forced); Haaland blank; **bench-fix shipped** |
| 19 | 51 | 40 | ROLL, refused churn (Rice injured); Enzo/Mateta 9 |
| 20 | 53 | 42 | Cascade reshape (→Tarkowski, →Semenyo); Thiago 17 |
| **Σ** | **1140** | **1002** | **+138; hits: 1; captaincy 20/20** |

## Recent session log

- **2026-07-23 (GW18-20 session, `@next-sim` ×3):** ran three GWs through the festive/AFCON
  cascade with parallel point-in-time research agents. **Shipped the bench-order fix**
  (`reselect_xi`, the #1 [OPEN] since GW10) after it surfaced trying to start a banned
  Szoboszlai. Applied the new co-equal Manager's Read doctrine (Cunha buy, roll-refusing-Rice,
  EV-over-trajectory Semenyo call). +116 → +127 → +138. Three captain blanks weathered by squad
  depth. See gwNN.md / reviews/gwNN.md GW18-20.
- **2026-07-23 (earlier):** GW17 AFCON reshape (Mbeumo→Foden, Muñoz→Keane), 1000-pt milestone;
  then promoted the human overlay to a co-equal Manager's Read (owner directive) across
  knowledge.md + the plan-gameweek/review skills.
- **2026-07-22:** built the season-replay harness (GW1–10 gate, +93); GW11-16 disciplined rolls
  (658→941). Six model/policy fixes; decision architecture (plan.md, consensus, duel lens).

*Keep this file current: overwrite "Where things stand"/"next session" each session; append to log.*

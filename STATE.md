# Session State — updated 2026-07-22

*Handoff snapshot for the next session. Read this first, then `NEXT-STEPS.md`
for the full roadmap. GW1 deadline ≈ mid-August 2026 (~3 weeks out).*

## Where things stand

- **Code: done and green.** 29/29 tests pass, 0 skipped (Dixon-Coles fit test
  now runs — penaltyblog installs via the SessionStart hook). Ruff clean.
- **Sessions bootstrap themselves.** `.claude/hooks/session-start.sh` (on
  `main`) installs `dev`/`models`/`optimize` extras + penaltyblog at web-session
  start. No manual pip steps.
- **No live data has ever been pulled.** No `db/`, no snapshots, no decision
  memos, no weekly reports. Everything downstream of the first snapshot is
  still pending.
- **Ruleset unverified.** `config/rules/2026-27.yaml` has
  `verified_against_official: false`; the optimizer refuses real runs until
  season-launch verification (correct behavior — game hasn't opened).

## Network reality (tested 2026-07-22, details in `docs/environment.md`)

| Route | Status |
|---|---|
| PyPI / package registries | ✅ works |
| github.com + raw.githubusercontent.com | ✅ works — vaastav/FPL-Core-Insights pulls possible **today** |
| WebSearch (server-side) | ✅ works |
| FPL API, football-data.co.uk, all news domains, WebFetch | ❌ egress-policy 403 |

**Owner action pending:** allowlist `fantasy.premierleague.com` and
`www.football-data.co.uk` (full list in `docs/environment.md`) in the
environment settings on claude.ai/code. Re-test with the curl one-liner in that
doc at the start of the next session — if 200, NEXT-STEPS §1 (first live
snapshot) is unblocked.

## What the next session should do (in order)

1. **Re-test network.** If unblocked → run NEXT-STEPS §1 (first snapshot,
   DuckDB build, football-data fetch, first projections, price radar) with its
   sanity checks.
2. **Regardless of network:** start NEXT-STEPS §2 (backtest gate) — the
   vaastav + FPL-Core-Insights data is on GitHub and reachable now. This is
   the non-negotiable pre-GW1 gate and needs no policy change.
3. When the 2026/27 game opens: rules verification (NEXT-STEPS §3).

## Intelligence gathered this session (verify before relying on it)

WebSearch on announced 2026/27 rule changes (sources: premierleague.com
2026-07, Fantasy Football Scout 2026-07-20) — pre-verification signal for the
`config/rules/2026-27.yaml` reconciliation:

- Chips **unchanged**: two sets (WC/FH/TC/BB) per half-season.
- Transfer bank kept at **5**; no extra December transfers (no AFCON this season).
- BPS rebalanced: CBI threshold 3 (was 2), no BPS penalty for being tackled —
  aimed at reducing overlap with defensive-contribution points.
- New: real-time league/bonus updates, official price predictions in-app.
- Assistant-manager chip: **no mention** in announcements — likely gone, confirm.

## Recent session log

- **2026-07-22** (this session): verified project state; fixed `fpl-claude/`
  subfolder path drift across docs/skills; added SessionStart hook +
  `docs/environment.md`; merged as PR #1 (`f98248f`). A parallel session added
  `docs/brand/bio.md`.

*Keep this file current: overwrite the "Where things stand" / "next session"
sections each session and append to the session log.*

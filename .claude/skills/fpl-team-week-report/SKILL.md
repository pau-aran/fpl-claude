---
name: fpl-team-week-report
description: Weekly report on every Premier League team — results in ALL competitions (PL, UCL, UEL, UECL, FA Cup, EFL Cup), injuries picked up/cleared, press-conference notes, fixture congestion, and rotation-risk implications for FPL. Run every Monday and after midweek European/cup rounds, or when the user asks for the weekly team report.
---

# Weekly All-Team Report

You are fpl-claude (see root CLAUDE.md). Produce the weekly report covering **all 20 PL
teams** — the Moneyball scouting document that feeds every other decision.

## Steps

1. **Snapshot + skeletons.** From `fpl-claude/`:
   ```bash
   python -m fpl_claude.data.fpl_api snapshot
   python -m fpl_claude.reports.team_week
   ```
   This writes `reports/weekly/{YYYY-WW}/{team}.md` skeletons pre-filled with PL
   results (last 7d), PL fixtures (next 14d, with FDR), and FPL-flagged players.

2. **Enrich every team file** — fill the three `<!-- skill: ... -->` sections using
   WebSearch/WebFetch over `fpl-claude/config/sources.yaml` sources:
   - **Other competitions:** which UCL/UEL/UECL/FA Cup/EFL Cup matches did the team
     play this week, and what's scheduled in the next 14 days? Note minutes given to
     key FPL assets and any surprise rests/starts. (BBC Sport + UEFA.com + club news.)
   - **Injuries & pressers:** injuries picked up or cleared this week beyond FPL
     flags; manager press-conference quotes on fitness/rotation (Premier Injuries,
     FFScout team news, Sky, X via web search — @FPLStatus first). Cite the source
     inline for every claim.
   - **FPL takeaways:** 2–4 bullets — rotation risk verdict for congested teams,
     assets to buy/sell/hold/watch, price-movement pressure.

3. **Rewrite the index** (`index.md`): keep the table, then add a "**Biggest FPL
   takeaways this week**" section — the 5–8 things that should change decisions
   (injury to a template player, congestion cluster, a team's underlying numbers
   diverging from results).

4. **Congestion math matters:** a team playing Thu UEL → Sun PL → Wed cup has three
   games in 7 days; flag rotation risk HIGH for its non-nailed assets. Teams out of
   all cups get a "fixture-proof" tag — their assets carry a hidden premium.

5. Commit the week's report directory with message `weekly report {YYYY-WW}`.

## Rules

- Every injury/rotation claim needs an inline source. No source, no claim.
- Distinguish FPL API flags (mechanical) from news intelligence (your edge).
- Pre-season (before GW1): "last 7 days" covers friendlies — fill them from web
  search into the Other competitions section; minutes in friendlies are the best
  early minutes-model signal.

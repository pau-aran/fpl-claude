---
name: fpl-chip-strategy
description: Maintain the season chip calendar — detect double/blank gameweeks from fixture changes, plan wildcard/free-hit/bench-boost/triple-captain timing, and re-plan when fixtures move. Run weekly and whenever fixture changes or postponements are announced.
---

# Chip Strategy

You are fpl-claude. Chips are the highest-leverage decisions of the season; they are
planned on a calendar, never spent on impulse.

1. **Verify chip inventory** against `config/rules/2026-27.yaml` — while the chips
   section is unverified, plans are provisional and say so.
2. **Fixture diff:** compare the latest two fixture snapshots (db/raw/*/fixtures.json)
   for moved/postponed/unscheduled matches; search @BenCrellin (via web search) and
   FFScout for DGW/BGW projections — cup runs and European finals create them.
3. **Maintain `fpl-claude/decisions/chip-calendar.md`:** for each chip — target GW
   (or window), trigger conditions, and the abort condition. Standard shapes: bench
   boost on a big DGW; triple captain on a premium's DGW; free hit on the biggest
   BGW; wildcards ahead of fixture swings/international breaks.
4. On any change: update the calendar with a dated changelog entry and commit.

A chip is only ever recommended in /fpl-plan-gameweek if the calendar (or an
explicitly reasoned override) supports it.

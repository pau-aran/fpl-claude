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
3. **Run the model-driven chip-EV surface** (`src/fpl_claude/optimize/chip_timing.py`) —
   the calendar is seeded by the model, not hand-guessed. `detect_double_blank` flags
   DGW/BGW teams from the fixtures table; `chip_surface` scores every future `xpts_gw{n}`
   (TC extra = the best captain's single-GW xpts; BB extra = the four bench players' xpts,
   with minutes-nailedness); `advise` applies the encoded rule (TC on a standout/DGW
   captain; BB only on a fully-nailed DGW; WC/FH only on a 4+ change need or a BGW/DGW —
   conservative default: HOLD, one chip per half-season). Backtest: `python -m
   fpl_claude.backtest.run --data DIR --season 2025-26 --gw N --out DIR --state PATH
   --propose` prints the chip-advice block (current-half verdicts + a forward EV surface).
   Live: call the same functions over the live projections once live data exists.
4. **Maintain `decisions/chip-calendar.md`:** for each chip — target GW
   (or window), trigger conditions, and the abort condition. Standard shapes: bench
   boost on a big DGW; triple captain on a premium's DGW; free hit on the biggest
   BGW; wildcards ahead of fixture swings/international breaks. Reconcile against the
   surface's verdicts (step 3) and record any human override with a written reason.
5. On any change: update the calendar with a dated changelog entry and commit.

A chip is only ever recommended in /fpl-plan-gameweek if the calendar (or an
explicitly reasoned override) supports it.

---
name: fpl-plan-gameweek
description: The main decision pipeline — refresh data, sweep news, run projections and the optimizer (when built), apply the Moneyball overlay, and write the gameweek decision memo (transfers, XI, captain, chip, EV, risks) for the owner to apply manually in the FPL app. Run at T-48h, T-24h, and a final T-2h check before each deadline.
---

# Plan Gameweek

You are fpl-claude. The output is `fpl-claude/decisions/gw{NN}.md` — the owner
applies it manually; you never touch their FPL account.

## Pipeline

1. **Refresh:** run /fpl-refresh steps; confirm next deadline via
   `fpl_claude.data.fpl_api.next_deadline()`. State time remaining.
2. **News:** run /fpl-news-sweep — the risk table goes into the memo.
3. **Project:** Phase 2+ — run xPts models; until then, use the /fpl-scout proxy
   (form + FDR + flags + congestion from the latest weekly team report) and label
   it as proxy.
4. **Optimize:** Phase 3+ — run the MILP (refuses if ruleset unverified). Until
   then, reason the transfer/captain/bench decisions explicitly against
   `config/rules/2026-27.yaml` constraints and policies by hand.
5. **Overlay (the part only you can do):** deviate from the optimizer only with a
   written reason (presser tone, rotation pattern from the weekly report, tactical
   change). Check every recommended player against the risk table — a flagged
   player needs a documented plan.
6. **Policies:** hits only if EV gain > `policies.hit_ev_threshold`; captain from
   an EV table (show top 3 with ceiling/floor); respect chip calendar.

## Memo format (`decisions/gw{NN}.md`)

- **Header:** GW, deadline (UTC + time remaining), squad value, bank, free transfers.
- **Transfers:** OUT→IN with EV delta and rationale; hits justified against threshold.
- **XI + bench order + captain/vice:** captain EV table.
- **Chip decision:** use/hold, vs the calendar.
- **Risk table** (from news sweep) + what we're deliberately fading (the template
  deviation and why).
- **Plan B:** the fallback if a flagged player is ruled out at T-2h.
- Commit the memo. At T-2h: re-verify flags only; if nothing changed, confirm the
  memo stands ("FINAL"); if something changed, apply Plan B, mark the edit, commit.

Never let the deadline pass without a FINAL memo — a legal recommendation from
cached data always beats silence.

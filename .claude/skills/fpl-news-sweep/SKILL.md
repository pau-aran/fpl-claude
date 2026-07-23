---
name: fpl-news-sweep
description: Sweep injuries, press conferences, lineup leaks, X/Twitter signals, and FPL strategy-page consensus into a structured risk table. Run daily and always before a deadline. Use when the user asks about injuries, team news, or "what's the word" on a player.
---

# News & Intelligence Sweep

You are fpl-claude. Work through `config/sources.yaml` by tier using
WebSearch/WebFetch. X/Twitter is reached via web search (search the handle + topic,
e.g. "FPLStatus <player>"), never a paid API.

## Sweep order

1. **Tier 1:** FPL API flags (fresh snapshot), @FPLStatus via search, Premier
   Injuries table, FFScout team news.
2. **Press conferences** (pre-deadline: mandatory): each PL manager's presser
   quotes on injuries/rotation — search "<manager> press conference" + date.
3. **Strategy consensus:** FFScout articles, r/FantasyPL front page, LiveFPL
   template/effective-ownership, FPL Statistics price predictions.
4. **@BenCrellin** via search for any fixture-change/DGW/BGW news → if found,
   flag that /fpl-chip-strategy must re-run.

## Output — the risk table

| Player | Team | Status | Source(s) | Confidence | FPL impact |
|---|---|---|---|---|---|

- Status: FIT / KNOCK / DOUBT / OUT(+return est.) / SUSPENDED / ROTATION-RISK
- Confidence: OFFICIAL (club/FPL flag) / STRONG (beat reporter, presser quote) /
  RUMOUR (aggregator, community). Never present RUMOUR as fact.
- FPL impact: one clause — "hold", "sell before Friday price drop", "captaincy doubt", etc.

**Mandatory minutes red-alerts** (minutes are the stated #1 inefficiency):
- **Two consecutive 0-minute appearances** by an owned/shortlisted nominal
  starter, with no injury flag, is escalated to a DOUBT with a forced
  presser / beat-reporter check. Autosubs mask it, but a non-playing starter is
  a squad hole (GW15-16 Muñoz, £6.0 nominal starter, 0 min both weeks).
- **A `SUSPENDED` status needs TWO facts, not a headline:** the offence AND
  confirmation the ban is upheld/served against the club's expected team sheet
  or an official source — not an aggregator "X banned" line. **On ambiguity,
  default the player to AVAILABLE** — an erroneous 0.0 that benches a real
  starter is costlier than the missed suspension (GW9-10 Ballard was flagged
  banned but played both weeks).

Below the table: **Market notes** (predicted price changes affecting our squad or
shortlists) and **Strategy-page consensus** (what the crowd is converging on — we
need to know the template to know where our edge deviates from it).

Save nothing for pre-season sweeps unless asked; in-season, append the table to the
current gameweek's decision memo draft if one exists.

## Overlay keys the sweep produces

The sweep's findings become the `--overlays` JSON `{player_id: {...}}` the
projection pipeline consumes. Beyond availability, watch for **penalty-duty
changes** — a new taker (transfer, incumbent injured/dropped, new manager) is a
news event, not a stat, and his `xg90` lags his new role by weeks:

- `start_share` (0–1) + `reason`: minutes/availability, as usual.
- `duration_gws`: how many horizon GWs the news SUPPRESSION covers. Short
  durations are OPT-IN — knock → 1-2, "out weeks" → 3-4, ban → matches
  remaining, structural/season-ending/departure → **OMIT** (whole horizon, so
  an ACL or transfer never "recovers"). Omit for near-1.0 confirmations too;
  scoping only matters for suppressions. **When unsure, omit** — an erroneous
  short scope re-poisons the horizon and manufactures a phantom sale (the
  GW2-4 defect that was the season's binding constraint).
- `pen_boost` (0–1): set when a player has just BECOME the designated penalty
  taker and the snapshot's `penalties_order` hasn't caught up. It forces the
  xPts penalty term on for that player (1.0 = full spot-kick credit). Leave unset
  for an established taker — his pens are already in his xg90 and the model prices
  them without help. Always pair it with a sourced `reason`.

# FPL sources reference — field-tested

*Refined from the 2025/26 backtest replay (GW1–4, ~200 verified pre-deadline
facts): only sources that actually answered an FPL decision question are
listed, tiered by what they uniquely provide. `config/sources.yaml` remains
the live sweep config; this file is the evidence-based reference behind it.
Keep it FPL-only and current: add a source when it proves out, remove one
that stops earning its slot.*

## 1. Availability & team news (the biggest single edge)

| Source | Proven for | Notes from the replay |
|---|---|---|
| Fantasy Football Scout — live team-news blogs | Friday presser aggregation, predicted lineups | Decisive in GW2/GW4 overlays; the single best pre-deadline page |
| Official club sites (arsenal.com, mancity.com, chelseafc.com, manutd.com, liverpoolfc.com, tottenhamhotspur.com…) | Injury confirmations, surgery statements, signings | Primary-source truth: Colwill ACL, Kovacic surgery, Kepa role |
| Sky Sports | Transfers, injury timelines, standoffs | Fast and reliable; Isak/Wissa sagas, Maddison ACL |
| BBC Sport | Injury reporting, transfer confirmations | Steady corroborator (Wissa, Dúbravka) |
| premierleague.com news | Official injury/signing announcements | Trafford signing, Colwill surgery |
| ESPN | Exclusions/standoffs, lineup reports | Isak exclusion, Garnacho deal, GW lineups |
| knocksandbans.com | Suspension lengths (red-card bans) | Answered Konsa DOGSO = 1 match vs Gordon SFP = 3 |
| Sports Mole injury lists | Per-club consolidated absence lists | City multi-absence weeks |
| Goal.com lists/pressers | Presser quotes, "bomb squad" situations | Verbose but frequently first with quotes |
| Wire syndications (PA via Yahoo/AOL/Malay Mail) | Presser quotes when primary pages are blocked | Useful fallback when snippets are all you can read |
| RotoWire / 101greatgoals | Confirmed starting XIs (post-team-sheet) | Reveals keeper pecking orders for the NEXT deadline |

## 2. Averages, benchmarks & meta

| Source | Proven for |
|---|---|
| FPL-Core-Insights (github.com/olbauday/FPL-Core-Insights) | Official per-GW averages/highest scores via API mirror — reachable when the FPL API isn't |
| FPL Dave, FPL Pulse, AllAboutFPL | Independent per-GW average corroboration |
| LiveFPL | Effective ownership, top-10k template (NOT reachable headless — search snippets only) |

## 3. Underlying numbers & datasets (backtests, priors, training)

| Source | Proven for |
|---|---|
| FBref — Premier League (fbref.com/en/comps/9/) | THE reference for underlying stats: Opta xG/xA/npxG, per-90s, shooting, progressive actions, possession-adjusted defensive stats (tackles+interceptions ≈ DC-relevant), keeper PSxG. Use to sanity-check our rates layer and to price DC potential; owner-suggested, added GW5. Headless fetch may be blocked — read via search snippets or its StatHead tables |
| vaastav/Fantasy-Premier-League | Per-GW history: merged_gw, players_raw, fixtures — the backtest backbone. CAUTION: players_raw is end-of-season state (team/position/price leak January moves); point-in-time values must come from merged_gw |
| FPL-Core-Insights | bootstrap-static mirrors incl. event averages, FPL-ID-keyed |

## 4. Retired from the active list (kept in sources.yaml only if re-proven)

- Generic tactical long-reads (The Athletic) — never decided an overlay in 4 weeks.
- FPL Statistics price predictor — price moves are IN the vaastav replay data;
  for live seasons re-evaluate at season start.
- football-data.org API — congestion tracking never fed a decision yet;
  re-add when European weeks begin (GW6+ of a live season).

## Method notes (what made facts usable)

- A fact is only usable if PUBLIC BEFORE the deadline — every overlay entry
  carries source + date; "reported ~09:46 on deadline day" gets flagged.
- Keeper competitions are encoded as probabilistic splits (0.65/0.35), then
  updated the week after team sheets reveal the answer.
- Ban lengths need the OFFENSE (DOGSO 1 match, serious foul play / violent
  conduct 3) — never assume from "red card" alone.

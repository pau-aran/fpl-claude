# FPL sources reference — field-tested

*Refined from the 2025/26 backtest replay (GW1–4, ~200 verified pre-deadline
facts): only sources that actually answered an FPL decision question are
listed, tiered by what they uniquely provide. `config/sources.yaml` remains
the live sweep config; this file is the evidence-based reference behind it.
Keep it FPL-only and current: add a source when it proves out, remove one
that stops earning its slot.*

## 0. Core data architecture (owner-set, 2026-07-22)

**Official FPL API + Understat cover ~90% of the signal** (form, fixtures,
ownership, prices, underlying xG/xA). Community sources (Reddit, X) are the
**last-mile layer** — press-conference nuggets, rotation risk, set-piece order
changes — wired in as a lightweight news check before the transfer/captain
decision, never as the core pipeline.

| Layer | Source | What it carries |
|---|---|---|
| Core | `fantasy.premierleague.com/api/bootstrap-static/` | Whole player pool: form, basic xG/xA, ownership, price, ICT — single unauthenticated JSON call |
| Core | `…/api/fixtures/` | Fixture difficulty, kickoffs, blank/double GW detection |
| Core | `…/api/entry/{id}/` + `/history/` | Any team's picks/history (public read-only; we never authenticate — owner submits moves manually) |
| Core | Understat | Free per-shot xG/xA depth beyond the FPL API's basics; JSON embedded in page, scrapable |
| Last-mile | r/FantasyPL, curated X list (§5) | Team-news sentiment, rotation eye-test, consensus |

Typed/GraphQL wrappers exist if raw JSON ever grates (`fpl-api` by flavnat;
`fplscrapR` for R) — not currently used; raw JSON + pandas is fine.

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
| LiveFPL | Effective ownership, top-10k template (NOT reachable headless — search snippets only). **Also the de facto standard for price-change prediction** (rise/fall tonight, from net transfers) — the price radar for a live season |
| r/FantasyPL | Team-news sentiment, rotation-risk eye-test, captaincy polls that surface consensus fast. Programmatic access is straightforward via the Reddit API (PRAW) if the sweep ever needs to pull top posts/comments instead of web search |

## 3. Underlying numbers & datasets (backtests, priors, training)

| Source | Proven for |
|---|---|
| xG Stat (xgstat.com) | **The live-season advanced-stats reference from 2026/27**: FBref killed its advanced-stats feed in Jan 2026 and xG Stat is where most of the community moved (owner-flagged, 2026-07-22). Verify coverage (xG/xA, per-90s, defensive stats) at season launch |
| Understat | Free per-shot xG/xA — depth the FPL API lacks; JSON embedded in the page, scrapable. Core layer (§0), also the priors/training feed |
| FBref — Premier League (fbref.com/en/comps/9/) | HISTORICAL ONLY since Jan 2026 (advanced-stats feed discontinued). Still the reference for pre-2026 underlying stats used in backtests/priors: Opta xG/xA/npxG, per-90s, possession-adjusted defensive stats, keeper PSxG |
| vaastav/Fantasy-Premier-League | Per-GW history: merged_gw, players_raw, fixtures — the backtest backbone. CAUTION: players_raw is end-of-season state (team/position/price leak January moves); point-in-time values must come from merged_gw |
| FPL-Core-Insights | bootstrap-static mirrors incl. event averages, FPL-ID-keyed |

## 4. Retired from the active list (kept in sources.yaml only if re-proven)

- Generic tactical long-reads (The Athletic) — never decided an overlay in 4 weeks.
- FPL Statistics price predictor — superseded: LiveFPL is the de facto
  price-prediction standard (owner call, 2026-07-22); price moves are IN the
  vaastav replay data anyway.
- football-data.org API — congestion tracking never fed a decision yet;
  re-add when European weeks begin (GW6+ of a live season).

## 5. X/Twitter accounts (community strategy & consensus)

*Vetted July 2026 against the 2025/26 season. Reached via web search only
(`site:x.com <handle> <topic>` or handle + topic) — no paid API. X's API is
paid-tier and rate-limited, and direct scraping is fragile/ToS-risky, so this
stays a curated-list-via-search operation; if team-news SPEED ever becomes the
bottleneck in a live season, the stable upgrade path is RSS/Discord relay bots
that repost verified beat-reporter tweets, not the X API (owner note,
2026-07-22). X's role: team-news breakers and set-piece-order updates faster
than any API reflects them — last-mile input, never the core pipeline. TIER 1 =
read every deadline; 2 = pre-deadline and weekly; 3 = as needed.*

| Handle | Tier | Category | What it uniquely provides (evidence of quality) |
|---|---|---|---|
| @OfficialFPL | 1 | Official | Announcements, deadlines, price changes — primary source |
| @FPLStatus | 1 | Data/speed | Automated flags, confirmed lineups, provisional bonus, price changes — fastest mechanical feed |
| @BenCrellin | 1 | Data | The DGW/BGW fixture-planning authority (legendary spreadsheets); also all-time #1 ranked manager |
| @FFScout_ | 1 | Team news | FFScout feed: presser aggregation + predicted lineups — proven decisive in our GW2/GW4 backtest overlays |
| @LetsTalk_FPL | 1 | Strategy | Andy: transparent full-reasoning decision content; 588th overall 2025/26, 3x top-10k in last 6 seasons |
| @theFPLkiwi | 2 | Data/model | Open xPts/xMins projection model, npxG & finishing analysis — best public model to cross-check ours |
| @FPLPriceChanges | 2 | Data | Nightly predicted risers/fallers (LiveFPL engine) — the live price-change radar |
| @LiveFPL | 2 | Data | Effective ownership + top-10k template composition — the EO-risk input |
| @FPL_Rockstar | 2 | Speed | Earliest reliable lineup leaks pre-deadline ("the OG of team leaks"); 7x top-40k |
| @FPL_Harry | 2 | Strategy | Deadline decision threads with reasoning; 5 consecutive top-10k finishes before 2025/26 |
| @FPL_Heisenberg | 2 | Strategy | BBC Sport FPL expert (Wes Prickett); 7x top-30k, best 836th |
| @FPL_Salah | 2 | Elite transparency | Abdul Rehman: posts own team + transfer plans with reasoning; consistent elite ranks |
| @BigManBakar | 2 | Elite transparency | Posts own team with reasoning; 4th in the world 2024/25 |
| @FPLGeneral | 3 | Elite transparency | FFScout trusted veteran (multiple top-500s); weekly reveal = a template proxy |
| @FplRichard | 3 | Strategy/model | FPL Review author — solver-adjacent commentary |
| @robtFPL | 3 | Data | Betting spread-market graphics — market-implied goals/cards |
| @allaboutfpl | 3 | Strategy | Presser aggregation, captain-metric and wildcard-draft articles |

Dropped after vetting: FPLFamily, FPLMate, FPLHints (activity or decision-grade
content unverifiable for 2025/26); AlwaysCheating (podcast ended its run May 2025).

**Method note — consensus is an input, never an order.** Community/elite
consensus from these accounts is a roadmap for effective-ownership risk
management: it tells us what the market will punish us for missing (e.g. a
67%-polled captain) and where crowds are moving before price changes. It never
decides a move by itself. Any divergence from a clear template move — and any
follow of one against our model — requires a written reason in the gameweek
decision memo, with the EV at decision time.

## Method notes (what made facts usable)

- A fact is only usable if PUBLIC BEFORE the deadline — every overlay entry
  carries source + date; "reported ~09:46 on deadline day" gets flagged.
- Keeper competitions are encoded as probabilistic splits (0.65/0.35), then
  updated the week after team sheets reveal the answer.
- Ban lengths need the OFFENSE (DOGSO 1 match, serious foul play / violent
  conduct 3) — never assume from "red card" alone.

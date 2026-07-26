---
name: fpl-team-week-report
description: Weekly report on every Premier League team — results in ALL competitions (PL, UCL, UEL, UECL, FA Cup, EFL Cup), injuries picked up/cleared, press-conference notes, fixture congestion, and rotation-risk implications for FPL. Run every Monday and after midweek European/cup rounds, or when the user asks for the weekly team report.
---

# Weekly All-Team Report

You are fpl-claude (see root CLAUDE.md). Produce the weekly report covering **all 20 PL
teams** — the Moneyball scouting document that feeds every other decision.

## Steps

1. **Snapshot FIRST, then build skeletons.** From the repo root:
   ```bash
   python -m fpl_claude.data.fpl_api snapshot          # writes db/raw/YYYY-MM-DD/
   python -m fpl_claude.reports.team_week              # live API
   # or point-in-time / re-runnable:
   python -m fpl_claude.reports.team_week --from-snapshot 2026-07-25
   ```
   Flags: `--from-snapshot YYYY-MM-DD`, `--out-dir DIR`, `--raw-dir DIR`.
   The snapshot must come first: the **price & ownership movers** section diffs today's
   bootstrap against the newest strictly-older `db/raw/` snapshot. Skip a day of
   snapshots and that week's movers section degrades (it says so explicitly rather
   than going quiet). This is the reason to keep `/fpl-refresh` on a daily cadence.

   The builder writes `reports/weekly/{YYYY-WW}/{team}.md` + `index.md`, pre-filled with:
   PL results (last 7d), PL fixtures (next 14d with FDR), FPL-flagged players, and the
   movers diff. With `--from-snapshot` the week folder, the header and the 7d/14d windows
   all come from the **snapshot** date (via `meta.json` `fetched_at_utc`), never the wall
   clock — an old snapshot reconstructs the report as it would have been written.

2. **Enrich every team file** — fill the `<!-- skill: ... -->` sections using
   WebSearch/WebFetch over `config/sources.yaml` sources:
   - **Other competitions:** which UCL/UEL/UECL/FA Cup/EFL Cup matches did the team
     play this week, and what's scheduled in the next 14 days? Note minutes given to
     key FPL assets and any surprise rests/starts. (BBC Sport + UEFA.com + club news.)
   - **Injuries & pressers:** injuries picked up or cleared this week beyond FPL
     flags; manager press-conference quotes on fitness/rotation (Premier Injuries,
     FFScout team news, Sky, X via web search — @FPLStatus first). Cite the source
     inline for every claim.
   - **FPL takeaways:** 2–4 bullets — rotation risk verdict for congested teams,
     assets to buy/sell/hold/watch, price-movement pressure.

3. **Rewrite the index** (`index.md`): keep the table, then write the "**what changed
   this week that matters**" section — the 5–8 things that should change decisions
   (injury to a template player, congestion cluster, a team's underlying numbers
   diverging from results). The builder leaves a placeholder for it.

4. **Congestion math matters:** a team playing Thu UEL → Sun PL → Wed cup has three
   games in 7 days; flag rotation risk HIGH for its non-nailed assets. Teams out of
   all cups get a "fixture-proof" tag — their assets carry a hidden premium.

5. Commit the week's report directory with message `weekly report {YYYY-WW}`.

## Pre-season edition (before GW1)

The builder detects pre-season (`season_started()`: no event current/finished, no
fixture kicked off) and changes shape rather than emitting 20 files of "no matches":

- last-7-days becomes an explicit "season not started" line;
- the empty 14-day window falls back to the **opening run** (next 5 scheduled fixtures
  + average FDR);
- a `## Pre-season (filled by skill)` section appears;
- the index swaps its first two columns for **GW1 fixture** and **opening-5 avg FDR**,
  and carries the next-deadline countdown.

Enrich the pre-season edition with: **friendlies played** (score, date, minutes for key
assets — friendly minutes are the best early minutes-model signal), **confirmed
transfers in/out**, **injuries and expected return dates**, **manager change and
expected shape**, and the club's **2026/27 European commitment**. The European
commitment is the highest-value line in the whole pre-season edition: it sets the
congestion/rotation baseline for the entire season, so record it once, here, per club.

Also record on the FPL side: prices are frozen pre-season (`cost_change_start` is 0 for
every player until GW1), so the movers section will legitimately show nothing until the
game's price engine starts — do not read that as a builder failure.

## Rules

- Every injury/rotation/transfer/result claim needs an inline source: **a link AND a
  publication date**, e.g. `(BBC Sport, 2026-07-18, https://…)`.
- **Never invent** a score, fee, quote or date. If you searched and could not confirm
  it, write `unverified` and say what you looked for. This directory is an audit trail.
- Distinguish FPL API flags (mechanical) from news intelligence (your edge).
- Batch the research: 4–5 clubs per parallel search agent, one brief each, then write
  the files yourself. 20 clubs sequentially is not the deliverable's cost.
- Partial coverage is not the deliverable — all 20 clubs, every week.

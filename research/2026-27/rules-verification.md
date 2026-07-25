# 2026/27 ruleset verification

**Date:** 2026-07-25 · **File:** `config/rules/2026-27.yaml` · **Status:** VERIFIED —
`verified_against_official: true`, zero sections left flagged. The optimizer gate in
`src/fpl_claude/optimize/milp.py` (`RulesetUnverifiedError`) is now open.

## Sources, in order of authority

1. **`db/raw/2026-07-25/bootstrap.json`** — the live FPL API snapshot. `game_settings`,
   `game_config.rules`, `game_config.scoring`, `chips` and `element_types` are emitted by
   FPL itself and are machine-truth. Everything mechanical below comes from here.
2. https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627 — official 2026/27 changes article.
3. https://www.fantasyfootballscout.co.uk/2026/07/20/fpl-2026-27-5-rule-changes-new-features-announced — the 5 announced changes, with BPS detail.
4. https://www.premierleague.com/en/news/2174907 (FPL basics: transfers), https://www.premierleague.com/en/news/2174899 (managing your team) — FT/hit/auto-sub/captain mechanics.
5. https://www.draftfantasy.com/blog/fpl-defensive-contributions-2026-27 — DEFCON thresholds for 2026/27.
6. https://www.fantasyfootballfix.com/blog-index/fpl-2026-27-new-rules/ — chip deadline, BPS detail (partly contradicts source 3, see "Conflicts").

`https://fantasy.premierleague.com/help/rules` was fetched but returns only the SPA shell
(no rules text) — hence the API snapshot as primary source.

## Field-by-field

| Section | Field | Old | New | Source |
|---|---|---|---|---|
| top | `verified_against_official` | `false` | `true` | this exercise |
| top | `verified_on`, `verified_sources` | — | added | — |
| budget | `initial` | 100.0 | **unchanged** | `squad_total_spend` 1000 ÷ `ui_currency_multiplier` 10 |
| budget | `sell_price_rule` | half_profit_rounded_down | **unchanged** | `element_sell_at_purchase_price: false`, `transfers_sell_on_fee: 0.5` |
| squad | size / 2-5-5-3 / max_per_club 3 | as written | **unchanged** | `squad_squadsize`, `element_types[].squad_select`, `squad_team_limit` |
| lineup | starting 11, min 1/3/2/1 | as written | **unchanged** | `squad_squadplay`, `element_types[].squad_min_play` |
| lineup | `max_defenders/midfielders/forwards` | — | **added** 5/5/3 | `element_types[].squad_max_play` |
| lineup | `vice_captain`, `captain_multiplier` | — | **added** true / 2 | `sys_vice_captain_enabled: true`; PL "managing your team" |
| lineup | `auto_subs`, `bench_order_matters` | true | **unchanged** | PL basics: starter on 0 mins replaced by first eligible bench player, in bench order |
| transfers | `free_per_gameweek` | 1 | **unchanged** | PL FPL-basics transfers |
| transfers | `max_banked` | 5 ("verify unchanged") | **confirmed 5** | `max_extra_free_transfers: 4` → 1 + 4 = 5; PL + FFS both say "roll up to five" |
| transfers | `hit_cost` | 4 | **unchanged** | PL FPL-basics transfers ("four Fantasy points") |
| transfers | `max_per_gameweek` | — | **added** 20 | `game_settings.transfers_cap` |
| transfers | `bonus_free_transfers` | — | **added** 0 | **CHANGE vs 2025/26**: no extra December/AFCON free transfers, AFCON moves to Jun/Jul 2027 (FFS) |
| chips | `wildcard` | count 2, windows "one_per_half_unverified" | count 2, windows `[[2,19],[20,38]]` | `chips[]` `start_event`/`stop_event` |
| chips | `free_hit` | `"unverified"` | **count 2**, `[[2,19],[20,38]]` | `chips[]` |
| chips | `bench_boost` | `"unverified"` | **count 2**, `[[1,19],[20,38]]` | `chips[]` — note: playable in **GW1** |
| chips | `triple_captain` | `"unverified"` | **count 2**, `[[1,19],[20,38]]` | `chips[]` — note: playable in **GW1** |
| chips | `assistant_manager` | `"unverified"` | **count 0 — REMOVED** | absent from `chips[]`; all `game_config.scoring.mng_*` are 0 |
| chips | `sets_per_season`, `half_boundary_gw` | — | **added** 2, 19 | 8 chip rows = 2×4; first set stops at event 19 (deadline 13:30 GMT Sat 2 Jan 2027), no carry-over |
| chips | `one_chip_per_gameweek` | true | **unchanged** | official rules |
| scoring | appearance 1 / 2 | as written | **unchanged** | `short_play` 1, `long_play` 2 |
| scoring | goals GKP10/DEF6/MID5/FWD4 | as written | **unchanged** | `goals_scored` |
| scoring | assists 3 | as written | **unchanged** | `assists` |
| scoring | clean sheet GKP4/DEF4/MID1/FWD0 | as written | **unchanged** | `clean_sheets` |
| scoring | conceded per 2: GKP −1, DEF −1 | as written | **unchanged** | `goals_conceded` (MID/FWD 0) |
| scoring | saves per 3 = 1, pen save 5, pen miss −2, YC −1, RC −3, OG −2 | as written | **unchanged** | `game_config.scoring` |
| scoring | `bonus` [3,2,1] | as written | **unchanged** | award structure untouched |
| scoring | `bps_reworked` | — | **added** true | **CHANGE**: BPS internals reworked (see below) |
| scoring | DEFCON DEF 2 pts @ 10 CBIT | as written | **unchanged** | draftfantasy + PL: DEFCON retained as-is |
| scoring | DEFCON MID/FWD 2 pts @ 12 CBIRT | as written | **unchanged** | as above; `game_config.scoring.defensive_contribution` = {DEF 2, MID 2, FWD 2, GKP 0} |
| game_ops | new section | — | **added** | timezone UTC, GW1 deadline 2026-08-21T17:30Z, 09:00 lockdown, 20-min provisional bonus, daily price changes |

## What actually changed for 2026/27 (vs our speculative file)

1. **Assistant Manager chip is gone.** Our YAML carried it as "verify status". It is not in
   the API chip list and every manager-scoring key is zeroed. Removed (`count: 0`).
2. **Two chip sets confirmed for all four chips**, not just the wildcard: 2× WC, 2× FH,
   2× BB, 2× TC = 8 chips. First set expires at the GW19 deadline; unused chips do not
   carry over into the second half.
3. **Chip windows differ between chips.** WC and FH start at **GW2**; BB and TC start at
   **GW1**. Our chip-timing code must not assume a uniform GW2 start.
4. **No bonus free transfers this season.** 2025/26's extra AFCON-window free transfers are
   gone (AFCON 2027 is in June/July). Relevant to the existing GW18-24 AFCON backtest work —
   that window's extra-FT assumption does not carry to 2026/27.
5. **BPS internals reworked** (3-2-1 award unchanged): no BPS penalty for being tackled;
   clearances/blocks/interceptions now 1 BPS per **3** actions (was per 2); goalkeeper save
   scoring restructured to reduce DEFCON overlap and improve GK/full-back/attacker bonus
   prospects. Flagged as `bps_reworked: true` — **we do not model BPS**, so nothing breaks
   today, but any future bonus model must not reuse 2025/26 BPS weights.
6. **Operational timing changes:** gameweek lockdown moved to 09:00 UK the day after the
   last match (was 1h after final whistle); provisional bonus published from minute 20;
   live ranks/mini-leagues. Captured in the new `game_ops` section — affects when a
   `/fpl-review` run can trust final points, not the optimizer.

## Conflicts and judgement calls

- **GK BPS detail conflicts between secondary sources.** FFS says saves inside the box 3 /
  other saves 2 / big chance saved 1 / penalty save 8; FantasyFootballFix says 2 per save
  +1 for penalty-area +1 for big chance, penalty save 7. Not resolvable from the API (BPS
  weights are not published there) and **not modelled by us**, so the YAML records only
  `bps_reworked: true` rather than a number either source might have wrong.
- **`onsidearena.com/tips/fpl-rule-changes-2026-27` was discarded as unreliable.** It claims
  1 Free Hit, 1 Bench Boost, 1 Triple Captain and a surviving Assistant Manager chip, all
  directly contradicted by the API chip list. Do not cite it.

## Left unverified

Nothing in the YAML is left flagged. Two caveats worth stating loudly:

- **The official `help/rules` page was never machine-readable** (JS SPA returns an empty
  shell to WebFetch). Verification rests on the FPL API snapshot plus official
  premierleague.com editorial. For every mechanical field the API is strictly better
  evidence than the prose page; for `hit_cost` (4) and `free_per_gameweek` (1) the API
  publishes no field at all, so those two rest on premierleague.com prose alone. They are
  long-standing rules explicitly restated for 2026/27, so this is low risk — but they are
  the only two values without machine confirmation.
- **Mid-season changes are possible.** `bootstrap.events[].overrides` was checked and is
  empty for all 38 gameweeks today, but FPL can populate it later. `/fpl-refresh` should
  re-check `game_config` and `events[].overrides` against this YAML; the new
  `test_verified_2026_27_matches_the_api_snapshot` test in `tests/test_scaffold.py` pins
  the YAML to the snapshot so a drift shows up as a test failure.

## Test changes made

- `tests/test_scaffold.py`: `test_ruleset_loads_and_reports_unverified` →
  `test_ruleset_loads_and_is_verified` (now asserts the ruleset IS verified). Added
  `test_ruleset_verification_gate_still_detects_unverified_sections` so the gate keeps
  coverage, and `test_verified_2026_27_matches_the_api_snapshot` as a drift guard.
- `tests/test_optimizer.py`: `test_refuses_unverified_ruleset` now exercises the gate with a
  deliberately re-flagged deep copy instead of relying on 2026/27 being unverified. Added
  `test_runs_on_the_verified_2026_27_ruleset_without_override`.

`pytest -q`: 71 passed. `ruff check` on the touched files: no new findings (the 2 remaining
are pre-existing and also present in the untracked `.claude/worktrees/` copies).

# Season-open brief — 2026/27 FPL game is LIVE

*Manager brief, written 2026-07-25 from the first live snapshot of the season.
Source of truth: `db/raw/2026-07-25/` (append-only, gitignored — regenerate with
`python -m fpl_claude.data.fpl_api snapshot`).*

## The headline: we have real data

Every prior session in this repo ran on archived vaastav data because the FPL API and
news domains were unreachable (`docs/environment.md`). **That is no longer true.**
`https://fantasy.premierleague.com/api/bootstrap-static/` returned HTTP 200, 1.3 MB, and
the 2026/27 game is open with real prices. The environment doc is now stale on this point.

| Fact | Value |
|---|---|
| Snapshot | `db/raw/2026-07-25/` (bootstrap + fixtures + meta) |
| Players priced | 558 |
| Teams | 20 |
| Fixtures loaded | 380 (full season) |
| **GW1 deadline** | **2026-08-21 17:30 UTC** — 27 days out |
| GW2 / GW3 deadlines | 2026-08-28 17:30 / 2026-09-04 17:30 UTC |
| Managers already registered | 1,341,561 |
| Chips visible in API | 2× wildcard (windows GW2–19 and GW20–38) |

## League composition

Promoted: **Coventry (COV), Hull (HUL), Ipswich (IPS)**.
Relegated from 2025/26: Burnley, West Ham, Wolves.

## What the data already tells us (before any research)

1. **Prices are locked.** `cost_change_start` is 0.0 for all 558 players and
   `transfers_in_event` is 0 across the board. Pre-season price changes have not begun.
   *Manager implication:* there is **no price pressure justifying an early buy**. Our price
   discipline rule (PLAN §5) only ever moves the *timing* of a decided transfer — with the
   market frozen there is nothing to time. We take the full 27 days and buy on information,
   not on fear of a 0.1 rise.

2. **FPL's own team strength ratings are unpopulated** — `strength_attack_home/away` and
   `strength_defence_home/away` are **0 for all 20 clubs**. Only the per-fixture FDR is
   usable from the API. *Implication:* the Dixon-Coles team model fitted on real results
   matters more than usual this season-open, and any code path reading `strength_*` would
   silently read zeros. Flagged as a live defect risk.

3. **46 players carry an injury/doubt flag** on day one. Several are high-price assets
   with "expected back 21 Aug" — i.e. the day before the GW1 deadline. That is the classic
   season-open trap and is being verified against news rather than trusted.

4. **`team_join_date` gives us the transfer window for free** — 56 players have joined a
   club since 2026-06-01. This is a cleaner signal than transfer news for *who is registered
   where*, though it says nothing about whether they will start.

5. **New/renamed data fields worth exploiting:** `scout_news_link`, `scout_risks`,
   `defensive_contribution_per_90`, `region`, `birth_date`, `team_join_date`, `opta_code`,
   `can_select` / `can_transact`. `defensive_contribution` being a first-class per-90 field
   confirms the 2025/26 defensive-contribution scoring category survives into 2026/27
   (verified separately against the official rules).

## The opening fixture landscape

Full grid: [`fixtures-gw1-8.md`](fixtures-gw1-8.md). **No blanks and no doubles in GW1–8** —
a clean opening run, which means no early chip case and a pure "best 15" build.

Best 8-GW runs by summed FDR: **LIV 22**, then CRY / MUN / NEW / SUN on 23.
Worst: **BOU 28**, then EVE / IPS / LEE on 26.

The sharper signal is the **opening four**, because that is how long our GW1 squad has to
survive before free transfers can meaningfully reshape it:

| Team | GW1–4 fixtures | Sum FDR (1–4) |
|---|---|---|
| **LIV** | NEW(A)3, NFO(H)3, IPS(A)2, FUL(H)2 | **10** |
| **MUN** | HUL(A)2, IPS(H)2, EVE(A)3, MCI(H)4 | **11** |
| **SUN** | IPS(A)2, FUL(H)2, BRE(A)3, ARS(H)4 | **11** |
| **TOT** | BRE(A)3, NEW(H)2, NFO(A)3, EVE(H)3 | **11** |
| **LEE** | NFO(A)3, BRE(H)3, BHA(A)3, NEW(H)2 | **11** |
| **BRE / BHA** | — | **11** |
| **MCI** | BOU(H)3, CRY(A)3, COV(H)2, MUN(A)4 | **12** |
| **ARS** | COV(H)2, AVL(A)4, CHE(H)4, SUN(A)3 | **13** |

*Manager read:* **Liverpool and Manchester United own the opening month.** MUN's
HUL(A) + IPS(H) is the single best opening pair in the league — both against promoted
sides — which puts a spotlight on their attacking assets at GW1. Arsenal have a soft
opener (COV at home) and then a hard GW2–3 (AVL away, CHE home), so Arsenal assets are a
GW1-only play unless they are good enough to hold through the bump.

## Market state on day one

Full board: [`market-board.md`](market-board.md).

The template is already forming hard around two names:

| Player | Club | Pos | Price | Ownership |
|---|---|---|---|---|
| Haaland | MCI | FWD | £15.5 | **73.7%** |
| B.Fernandes | MUN | MID | £12.0 | **47.9%** |
| João Pedro | CHE | FWD | £7.5 | 47.2% |
| Szoboszlai | LIV | MID | £7.0 | 40.9% |
| Rogers | CHE | MID | £7.5 | 34.8% |

Haaland at 73.7% is a **structural fact, not an opinion**: not owning him is a 74%-of-the-field
bet that costs us badly on any week he hauls. He is £15.5m of a £100m budget — the whole
squad build is downstream of that single yes/no.

Notable budget enablers the market has already found: Diop (IPS) £4.0 at 21.4%,
van Ewijk (COV) £4.0 at 16.7%, Dubravka (TOT) £4.0 at 24.5%, Shaw (MUN) £4.5 at 18.1%,
Konsa (AVL) £4.5 at 18.4%.

## Open questions this brief does not answer

Handed to parallel research legs, landing in this directory:

- `transfers.md` — which summer moves are real, and who actually starts at the new club
- `fitness-returners.md` — the 46 flags verified, plus World Cup 2026 late returners
- `teams-managers.md` — new managers, systems, promoted-side enablers, European load
- `rules-verification.md` — the 2026/27 ruleset reconciled against the official source
- `consensus-template.md` — where the crowd is, and where it looks wrong
- `projections-run.md` — our own model output once last season's priors are bridged in

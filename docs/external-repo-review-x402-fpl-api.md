# External repo review: `dohyung1/x402-fpl-api`

**Reviewed:** 2026-07-23 · **Reviewer:** fpl-claude · **Verdict:** _adopt 2 data signals, skip the architecture._

Source: <https://github.com/dohyung1/x402-fpl-api> — "FPL Intelligence MCP Server."

## What it is

Two components bolted together:

1. **An FPL analysis engine** — 16 heuristic algorithms in `app/algorithms/`
   (captain, differentials, transfers, chips, DGW intel, hit analyzer, prices,
   rivals, league analyzer, live, news, scout, weight optimizer). Exposed as a
   **13-tool MCP server** (`mcp_server.py`, FastMCP) for Claude Desktop, and as a
   paid HTTP API (`app/main.py`, FastAPI).
2. **An x402 paywall** (`app/x402.py`) — HTTP 402 micropayments in **USDC on Base
   Sepolia**, verified on-chain via Web3.py, with a SQLite `used_tx_hashes` table
   for replay protection. Gates `/api/fpl/*` routes.

Tech: Python 3.12, `uv`, FastMCP, official FPL public API, shipped on PyPI as
`fpl-intelligence`.

## Head-to-head with our engine

Both solve the same problem with **opposite philosophies**:

| Dimension | x402-fpl-api | fpl-claude (us) |
|---|---|---|
| Core method | Top-down **weighted composite score**: normalize ~13 features to 0–1, sum with tuned coefficients, rank | Bottom-up **probabilistic EV**: Poisson / Dixon–Coles per scoring component → E[points] in real point units |
| Captain | `ppg×5.92 + form×3.43 + bonus×1.31 + pen×1.90 + xg90×1.07 + …`, then `base^0.9 × fixture_mult × num_fixtures` | Full xPts from minutes × per-90 rates × team model, summed over the horizon |
| Minutes | single `minutes_cert` heuristic term | LightGBM minutes model + team-news overlays (`models/minutes.py`) |
| Weight fitting | `weight_optimizer.py`: coordinate descent + pairwise refinement over historical **captain points** | rules-driven scoring (no free weights) validated by the backtest gate |
| Team strength | FDR multiplier `1 + ((3−fdr)/2)×0.30 + home` | Dixon–Coles goal model (`penaltyblog`), FDR fallback labeled per player |
| Delivery | MCP server + crypto paywall | Skills + decision memos, owner submits manually |

**Conclusion: architecturally we are ahead.** Their scores are ordinal rankings;
ours are point expectations in real units — the whole Moneyball thesis is EV per
£m you can write down and defend. Their weighted-composite captain model is a
*downgrade* from our EV model.

## What to skip, and why

- **The x402 payment layer** — out of scope. We run one team on read-only public
  data, never monetize, never connect to an account (operating principle #6).
- **Weighted-composite scoring / `weight_optimizer`** — coordinate-descent weight
  tuning against historical captain points is a proxy for what our backtest
  already does directly, and our EV model has no free weights to tune. No adoption.
- **Differentials, hit ROI (`is_hit_worth_it`), DGW detection, chip timing, rival
  / league trackers, price predictions** — all already covered, and covered
  better, by `/fpl-scout`, `/fpl-chip-strategy`, the MILP optimizer, `/fpl-review`,
  and the EV hit threshold in `config/rules/`. Their price model
  (`net_transfers < ~−50k ⇒ likely fall`) is cruder than a proper price-change
  model. No adoption.

## What is worth taking — two real gaps it exposed

A grep of `src/` confirms these are fields the external repo uses that **we do not
touch anywhere** in the model layer. Both already sit in our append-only `db/`
bootstrap snapshots — we simply never surface them into projections.

### 1. Set-piece / penalty duty — HIGH VALUE

Fields: `penalties_order`, `corners_and_indirect_freekicks_order`,
`direct_freekicks_order`.

We model xG/90 but have **zero forward-looking signal for who takes the
penalties**. This is exactly operating principle #2 — *minutes are the market
inefficiency* — and set-piece duty is the next inefficiency right behind it. When
a taker changes (a transfer, a new manager, an injury to the incumbent),
historical `xg90` lags reality by weeks, but `penalties_order` flips **instantly**
in the bootstrap. A penalty on the spot is worth roughly a fifth of a goal in EV;
being the designated taker is a durable, mispriced edge the crowd is slow to price.

Adoption path (deferred — structural model change, must clear the backtest gate):
- Extract the three `*_order` fields in `data/fpl_api.py` / `rates.py`.
- Add a penalty-EV term to `models/xpts.py` for the designated taker (order 1),
  guarded so it does not double-count pens already inside historical `xg90`.
- Expose taker status in `/fpl-scout` and `/fpl-news-sweep` overlays (a taker
  change is a news event, not just a stat).
- **Gate it:** re-run the 2025/26 backtest; keep only if it does not regress.

### 2. FPL's own `ep_next` — LOW COST, worth it

FPL publishes its own expected-points figure per player (`ep_next`, `ep_this`).
We don't read it. Nearly free value as:
- an **ensemble / sanity check** against our xPts — a large disagreement on a
  captain pick is a flag worth a human look;
- a **calibration baseline** in `/fpl-review` (predicted vs actual vs FPL's own).

Adoption path: add `ep_next` as a benchmark column in `models/projections.py`
output and reference it in the `/fpl-review` calibration table. No model change,
no gate needed.

## Recommendation

Adopt the **set-piece/penalty-duty signal** (behind the backtest gate) and the
**`ep_next` benchmark column**. Skip the composite-scoring engine, the weight
optimizer, and the entire x402/crypto layer. Net: the repo's real gift to us
isn't its code — it's the reminder that we're leaving set-piece duty on the table.

## Update — implemented (both signals shipped)

Both adopted signals are now in the pipeline; the composite engine, weight
optimizer, and x402 layer were skipped as recommended.

- **Penalty component in `models/xpts.py`.** A `penalty` term for the designated
  taker (`penalties_order == 1`), fixture-independent (a spot-kick is a spot-kick,
  so it is *not* attack-scaled — a modelling improvement over lumping pens into
  `xg90`). Double-count-guarded by an `embed_gap`: FPL's `expected_goals` already
  embeds an established taker's own pens, so the term credits only what a player's
  `xg90` cannot have captured — a priorless newcomer taker whose rate is shrunk
  toward replacement (auto, decaying to zero as his own minutes earn full weight),
  plus an explicit news overlay `pen_boost` for a mid-season duty change among
  established players. Steady state for an established taker: `embed_gap → 0`,
  `xg90` unchanged, zero double-count.
- **Taker columns + `ep_next`** in `models/projections.py`: `is_pen_taker`,
  `is_set_piece_taker`, and FPL's own next-GW expected points as a benchmark
  (never a model input).
- **Backtest fidelity:** `backtest/data.py` carries season-end `penalties_order`
  as a documented static proxy (the archive has no point-in-time order);
  `ep_next` is left absent (no honest point-in-time value).
- **Skills wired** so the signal is used, not orphaned: `/fpl-scout` (set-piece
  value lens + `ep_next` sanity), `/fpl-news-sweep` (the `pen_boost` overlay key
  for duty changes), `/fpl-review` (log `ep_next` alongside our xPts vs actual).
- **Tests:** `tests/test_models.py::test_penalty_term_credits_only_unpriced_takers`
  covers newcomer-credit, established-zero, decay, non-taker, `pen_boost`, and the
  keeper guard (37 pass).

**Gate re-run (PLAN §4, GW1–10 replay, this environment's vaastav snapshot):
659 → 659, zero committed decisions changed → no regression.** The penalty term
never fired on our (established) backtest squad because the archive's taker order
is static season-end — the signal's payoff is inherently forward-looking (a taker
who *changes*), which a static-order replay cannot exercise. So this is a
live-value addition proven **safe**, not proven profitable; its edge banks the
first time a penalty duty actually moves during the live season.

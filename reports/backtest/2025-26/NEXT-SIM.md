# Next-session runbook — simulate GW20–22

*Continuation of the 2025/26 backtest replay. Branch:
`claude/branch-analysis-optimization-n8q1f5`. Read `knowledge.md` (the codified
decision rules) and the GW17–19 `reviews/` before starting.*

## Where the replay stands (after GW19)

- **Season 1085 pts** vs baseline 960 (**+125**). `state.json`: **last_gw 19, 4 FT,
  bank £0.3.** Captaincy 18/19 weeks Haaland/Salah-tier, 1 hit all season.
- **Owned 15:** Dúbravka, Roefs (GK); Saliba, Calafiori, Senesi, Konaté, J.Timber
  (DEF); Szoboszlai, Brooks, B.Fernandes, Enzo, Schade (MID); Haaland, Mateta,
  Thiago (FWD). **No owned player is at AFCON.**
- **Benchmark averages:** GW20 **42**, GW21 **48**, GW22 **40** (still the
  Boxing-Day/AFCON low-scoring window; AFCON final ≈ 18 Jan 2026).

## 0. Prereqs (the replay data is gitignored — re-fetch it)

```bash
cd /home/user/fpl-claude
git fetch origin && git checkout claude/branch-analysis-optimization-n8q1f5
python -m fpl_claude.backtest.fetch --dest db/backtest --season 2025-26 --prior 2024-25
python -m pytest -q            # sanity: 40 pass
```

## 1. Per-gameweek loop (run for GW20, then 21, then 22 — in order)

For each `GW` in 20, 21, 22:

**a. See the raw proposal + fixture outlook**
```bash
python -m fpl_claude.backtest.run --data db/backtest --gw GW \
  --out reports/backtest/2025-26 --propose
```

**b. Build the news overlay** `reports/backtest/2025-26/overlays/gwGW.json`
(point-in-time only — nothing you couldn't know before that deadline):
- **AFCON:** any player still at the tournament stays suppressed
  `{"id": {"start_share": 0.0, "reason": "... still at AFCON"}}` with **no
  `duration_gws`** (whole-horizon — a tournament absence must not "recover").
  Check when each nation is knocked out; returnees become **buy candidates** the
  GW they're available (we sold Mbeumo at GW17 — re-buying a returning AFCON asset
  is a legit move IF his fixtures justify it, not reflex).
- **Congestion (GW20 is a busy January window):** if a full news sweep isn't
  possible, at minimum treat 2-games-in-3-days clubs as rotation-risk — this is
  the exact blind spot that cost GW18 (−21). Don't roll blind into congestion.

**c. Build the decision** `reports/backtest/2025-26/decisions_gwGW.json` — apply
the codified rules (`knowledge.md`), don't just take the optimizer's output:
- `ban`: any AFCON player still out (force-sell if owned; keep out of buys).
- `lock`: protect the core to **refuse the recurring Saliba→Timber phantom
  same-club swap** and in-form-differential churn the optimizer proposes weekly.
- `start`/`bench`: the manager XI override for a fixture read the model can't see.
- `captain`: **Haaland unless PRE-DEADLINE NEWS says otherwise — never a marginal
  (<~1 pt) switch off the ~90% EO shield, and never onto a minutes-flagged player**
  (this exact rule saved GW19 when B.Fernandes DNP'd).
- `max_transfers`: only spend FT on a clear minutes/EV upgrade; otherwise **bank**
  (cap 5). A **two-consecutive-0-minute** owned player is a forced sell (it flagged
  the GW19 Muñoz→Timber that returned 9).
- **On any FORCED buy, weight minutes-security over ceiling** (Gakpo blanked on 0
  min at GW17 because we took the ceiling play over a nailed one).
- Put the full reasoning in the decision JSON `reasoning` field.

**d. Verify, then commit the GW for real**
```bash
python -m fpl_claude.backtest.run --data db/backtest --gw GW \
  --out reports/backtest/2025-26 \
  --overlays reports/backtest/2025-26/overlays/gwGW.json \
  --decision reports/backtest/2025-26/decisions_gwGW.json --propose   # re-check
# drop --propose to execute (advances state.json, writes memo + player CSV):
python -m fpl_claude.backtest.run --data db/backtest --gw GW \
  --out reports/backtest/2025-26 \
  --overlays reports/backtest/2025-26/overlays/gwGW.json \
  --decision reports/backtest/2025-26/decisions_gwGW.json
```

**e. Write the review** `reports/backtest/2025-26/reviews/gwGW.md` (match the
GW17–19 format): score vs the average above, grade each decision **process-first**
(rule 3 — a good call with a bad outcome is still a good call), log the captain
slot separately, and flag any bench-order fixture miss.

## 2. After GW22 — wrap up

- Update `knowledge.md` season-context averages line (append GW20-22: 42/48/40,
  cum through 22 = 1090) and add/adjust any new [DONE]/[WATCH] learnings the three
  weeks surface.
- Update `baseline.md` (GW20-22 rows) and the `STATE.md` scoreboard + session log.
- `git add` the `reports/backtest/2025-26/` deliverables (NOT `db/` — gitignored),
  commit, and `git push -u origin claude/branch-analysis-optimization-n8q1f5`.

## Watch-list carried in

- **Congestion rotation** — the GW18 blind spot. January is busy; sweep before
  rolling.
- **AFCON returnees** — re-buy candidates as nations are eliminated (~GW21-22).
- **Brooks** (£5.0 fringe MID) is a near-dead bench slot; upgrade only if it also
  improves the XI, not for its own sake (bench economics).
- **Gakpo/Schade-type rotation risks** on the incoming transfers — confirm minutes.

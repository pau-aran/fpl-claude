# Season log — 2026/27

One row per gameweek, appended by `/fpl-review`. Append-only: never edit or reorder past rows.

`Ours` is our final GW score. `Avg` is FPL's official average entry score
(`events[N].average_entry_score`). `OR` is overall rank. Where a cell reads *unavailable*
the value could not be retrieved at review time and was **not** estimated — fill it in when
the source becomes reachable, in a new row-note rather than by editing history.

| GW | Ours | Avg | Δ | OR | Δ OR | Hits | Chip | Decision-quality note |
|---|---|---|---|---|---|---|---|---|
| 1 | ~48 (floor 41) | *unavailable* | — | *unavailable* | — | 0 | — | Predicted 51.41 (base 45.09 + cap 6.32); actual base ~46 (**+0.9**), captain slot 2 (**−4.3**). Captaincy 1/1, no auto-subs. World Cup **minutes** fade FAILED (all returners started; Guéhi/Saka/Rogers returned) but the sharpness read was right — Haaland 0.85 xG, no goal. B.Fernandes fade PASS (both he and Mbeumo ~2, ours £4.0m cheaper). Iteration-2 self-correction Nunes→Tarkowski worth **~+5**. Named duel (Mbeumo at Hull) FAILED. Missed De Cuyper 17 and Guéhi ~11 — both positional arbitrage. **Process failure: the T-48h re-solve never ran.** |

## Standing notes

- **GW1 numbers are reconstructed, not API-sourced.** The FPL API is blocked by the session's
  egress policy; appearance / clean-sheet / goal / assist / concession points are verified
  from match reports and confirmed line-ups, while saves, DefCon and bonus are not. The row
  quotes a verified floor and a central estimate. Re-derive from `event/1/live` when possible.
- **`notebooks/calibration.md` has no GW1 entry.** The calibration CLI needs the pre-deadline
  projections snapshot (`db/projections/`, local-only) and the live API. `--allow-post-deadline`
  was deliberately not used; the split is recorded in `reports/reviews/2026-27/gw01.md` §3
  instead, to be re-run for real when the data is reachable.

---
name: fpl-review
description: Post-gameweek retrospective — predicted vs actual points, luck vs process separation, model calibration log, and rank tracking. Run after each gameweek completes (or when the user asks how the team did).
---

# Post-GW Review

You are fpl-claude. Moneyball rule 3: judge the process, never the variance.

1. Pull final GW stats (`fpl_claude.data.fpl_api.get_event_live(gw)`) + fresh snapshot.
2. Against `decisions/gw{NN}.md`, score every decision:
   - each transfer: EV claimed vs points delivered (both players)
   - captain: chosen vs best-in-squad vs the EV table's alternatives
   - bench: points left on the bench; auto-subs that fired — and specifically,
     did we bench a player who then outscored a starter we picked in a HARDER
     fixture? Flag it as a fixture-softness ordering miss (the GW10/GW13 leak)
     and check whether a `start`/`bench` overlay was warranted.
   - chip (if used): realized vs planned value
3. **Separate luck from process:** a good decision with a bad outcome is logged as
   good process (and vice versa). One line each: "right/wrong for the right/wrong
   reason".
   - **Grade the Manager's Read (owner directive 2026-07-23):** for every call where the
     human read DEVIATED from the solve — a trajectory/eye-test transfer, a brave captain,
     a bench-order override — score whether the human overlay ADDED or LEAKED points vs what
     the model would have done. Keep a running tally so we measure over the season whether the
     co-equal human voice is a real edge (like the duel lens: 2 buy-side hits before it was
     called PROVEN). This is process-graded — a sound read that missed on variance still
     passes — but a read that is systematically wrong gets its rein pulled back.
4. Append one row to `decisions/season-log.md`: GW points, average, overall rank,
   rank delta, hits taken, decision-quality notes.
5. **Calibration — RUN IT, don't hand-write it.** Append this gameweek's
   predicted-vs-actual entry to `notebooks/calibration.md`:

   ```
   python -m fpl_claude.reports.calibration --gw {NN} [--squad PATH] [--chip NAME]
   ```

   The predicted side is the `db/projections/{YYYY-MM-DD}.csv` snapshot written
   **before** that GW's deadline (selected by date, post-deadline files refused and
   named in the log); the actual side is `event/{NN}/live`; the join key is the FPL
   player id. Pass `--squad` (a CSV of `id,role` with C/V/XI/bench) so the log can
   split what we OWNED from the pool at large — without it you only get pool metrics.
   Backtest weeks use `--actuals backtest --backtest-players reports/backtest/2025-26/gwNN_players.csv`.
   `--dry-run` prints the section without appending. If it refuses with a
   `PointInTimeError`, **do not** reach for `--allow-post-deadline` to make it pass —
   there was no pre-deadline projection, so there is nothing honest to calibrate.

   Then READ the output — the command produces evidence, you produce the judgement:
   - **Base XI vs captain slot are logged separately** (the memo Outcome prints the
     same split: "Predicted: T = base XI B + captain slot S"; see
     `reports/backtest/2025-26/calibration.md`). The 20-GW decomposition showed the
     residual is NOT captain-only: the small mean under-prediction (+4.3/GW) lives in
     the BASE XI and is within noise (t=1.47, ns), while the DOUBLED captain is
     mean-unbiased (−0.07) but high-variance — a blank/haul swings the total ±~10 on
     its own. Read EV/hit-gate reporting against that structure. It distorts reported
     EV, not the rankings (captaincy 20/20), so it is a reporting note, not a ranking
     bias.
   - **Per position**: a recurring one-sided error (e.g. the minutes model too
     optimistic on rotation-risk defenders) becomes a model TODO — but only if the
     `sig 5%` column says the mean is distinguishable from noise. One week is never
     enough; compare the row against the same row in past sections.
   - **FPL's `ep_next` is logged beside our `xpts_gwNN`** — two independent predictors
     framing the error. The log names the players where FPL's number beat ours: ask
     what it saw (usually minutes, or a set-piece/penalty role) and feed that back
     into the overlay or a model TODO. It is NaN in the backtest archive; the log says
     "absent" rather than faking a comparison.
   - **Owned vs whole pool**: the owned table is what actually cost us points, the
     pool table is model quality at large. A good pool with a bad squad is a
     selection problem, not a model problem.

   The log is append-only — never edit or reorder past sections.
6. End with max 3 lessons that change next week's behavior. No generic lessons.

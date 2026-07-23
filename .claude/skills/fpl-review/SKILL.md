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
   - bench: points left on the bench; auto-subs that fired
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
5. **Calibration:** once models are live, log predicted-vs-actual error per position
   into `notebooks/calibration.md`; recurring bias (e.g. minutes model too optimistic
   on rotation-risk defenders) becomes a model TODO. Log our `xpts_gwNN` **and** FPL's
   own `ep_next` against actual side by side — two independent predictors framing the
   error. Where FPL's number beat ours on a call, ask what it saw (usually minutes or
   a set-piece/penalty role) and feed that back into the overlay or a model TODO.
6. End with max 3 lessons that change next week's behavior. No generic lessons.

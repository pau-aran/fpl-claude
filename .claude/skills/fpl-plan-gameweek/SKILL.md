---
name: fpl-plan-gameweek
description: The main decision pipeline — refresh data, sweep news, run projections and the optimizer (when built), apply the Moneyball overlay, and write the gameweek decision memo (transfers, XI, captain, chip, EV, risks) for the owner to apply manually in the FPL app. Run at T-48h, T-24h, and a final T-2h check before each deadline.
---

# Plan Gameweek

You are fpl-claude. The output is `decisions/gw{NN}.md` — the owner
applies it manually; you never touch their FPL account.

## Pipeline

1. **Refresh:** run /fpl-refresh steps; confirm next deadline via
   `fpl_claude.data.fpl_api.next_deadline()`. State time remaining.
2. **News:** run /fpl-news-sweep — the risk table goes into the memo.
3. **Project:** run the pipeline —
   `python -m fpl_claude.models.projections --from-snapshot <today>` with
   `--overlays` built from the news sweep (each override = player id, start_share,
   written reason) and `--prior-snapshot` early season. Then the **consensus
   cross-check**: compare our captain top-3 and every transfer-in candidate against
   at least two public sources (LiveFPL, FPL Review free, FFScout). Big divergence →
   investigate (stale minutes intel? fix overlay and rerun) and record the verdict
   in the memo's "Consensus check" line. Benchmark, never input.
4. **Optimize:** run the live CLI — it drives the MILP, applies the hit gate and
   prints the sanity guards:

   ```bash
   # GW1 / wildcard (initial build) — newest db/projections/*.csv by default
   python -m fpl_claude.optimize.run_live --json decisions/gw01_solve.json
   # later GWs (transfer mode) — squad-state JSON: ids + buy costs (tenths),
   # bank, free transfers; format documented in run_live.py's docstring
   python -m fpl_claude.optimize.run_live --squad decisions/squad.json \
       --lock Saliba --ban "Pedro@Chelsea" --captain Haaland --max-transfers 1 \
       --json decisions/gw05_solve.json
   ```

   Overlay flags take **names or ids** (`--lock`, `--ban`, `--force-start`,
   `--force-bench`, `--captain`, `--vice`, `--max-transfers`); ambiguous names
   error with the candidates. Quote the `--json` dump's exact numbers in the
   memo (`ev_delta` against `policies.hit_ev_threshold` for any hit) rather than
   re-deriving them. Read its three guards before writing the memo: **club
   usage** (3-per-club concentration), **bench hairs** (every XI-vs-bench margin
   under 0.2 xPts — rule on each, `--force-start` to pull one), and the
   **minutes/flag** lists (`neutral` confidence, `low_sample`, FPL flags — at a
   season open that is most of the squad; every one needs the news sweep).
   It refuses while the ruleset is unverified: before season-launch
   verification pass `--allow-unverified` and label the memo "rules unverified
   — dry run" (the CLI labels its own output DRY RUN).
   - **Before the solve**, write the funding arithmetic of the route you intend
     (sells + bank ≥ buys, and the resulting squad is position-quota-legal). A
     route that doesn't foot cannot be the plan — say so and pick another.
   - **After the solve**, re-read the recommended move against that reasoned
     route. A `lock`/captain re-solve can silently redirect the transfer to a
     different player (it did twice — GW4, GW6). If it did, either fix the
     constraint or write a signed addendum; the memo's reasoning must name the
     move actually recommended.
   - The optimizer now picks the **XI, captain, vice and bench order on THIS
     week's fixture** (nearest `xpts_gw{n}`), not the multi-week horizon it buys
     the 15 on. Do not re-order the bench by the horizon column by hand.
4b. **Manager's Read — write it BEFORE you read the solve (co-equal voice, owner
   directive 2026-07-23).** The optimizer is one input, not the anchor; anchoring to
   the machine and rationalising afterward is the failure mode this prevents. In a few
   sentences, put down the HUMAN read: team trajectory / eye-test (manager-bounce sides,
   teams visibly clicking, players who look dangerous before the returns show, Christmas-
   congestion rotation feel, a squad gone thin/over-reliant), who's genuinely due vs cold,
   and who you'd want to watch live. Lean hardest into **team-trajectory/eye-test** and
   **captaincy bravery** (owner emphasis). One feeder of this read is the **positional-duel
   lens** (owner directive, 2026-07-22): name the in-form players facing a weak direct
   counterpart this GW (winger vs slow/exposed fullback, striker vs error-prone or stand-in
   CBs, attacking fullback vs a non-tracking winger, defence/GK vs a blunt attack) — team
   FDR hides soft individual duels.
5. **Reconcile the read with the optimizer (the part only you can do).** The Manager's Read
   carries REAL authority on the axes where models are weakest and feel is strongest —
   **bench order, captaincy, differentials-for-rank, riding-vs-fading runs** — and MAY
   override the solve there even against MODEST EV, provided it fits the plan and minutes are
   safe. It does NOT override: a flagged/benched-for-minutes player (the minutes gate is
   sacred — check every recommended player against the risk table), the plan's funding
   arithmetic, or a LARGE EV gap (the model still governs the big quant calls). Every
   deviation gets a written reason; every named read (trajectory call, brave captain, duel)
   goes into the memo so the review GRADES it — process, not outcome — and we measure over the
   season whether the human overlay adds or leaks points.
   - **Premiums are HOLDS through short-term (1-2 week) absences.** Refuse a
     lateral or cost-neutral swap that sells an established premium to patch one
     thin XI — bank the FT and accept a legal-but-thin formation; the absentee
     returns for ~0 cost (GW3 held Palmer; GW14 refused Saliba→Virgil on a
     one-week illness). Distinct from a genuine multi-week/season-ending loss,
     which IS replaced.
   - **Bench/XI order override (`start`/`bench` in the decision JSON):** the
     optimizer already orders the XI on this week's fixture, but it cannot see a
     depleted opponent defence or a soft individual duel. When you do, force the
     owned player in (`start`) or out (`bench`) with a written reason — the only
     tool that catches the GW13 class (started Calafiori at a depleted Arsenal
     over Konaté v West Ham, −8). Never start a nailed defender in a hard away
     trip over a nailed defender at home to a bottom side on tied projections.
6. **Policies:** hits only if EV gain > `policies.hit_ev_threshold`; captain from
   an EV table (show top 3 with ceiling/floor); respect chip calendar. Price
   pressure (from the refresh radar) may pull a decided transfer earlier in the
   window or delay a sale — it never changes WHO we buy or sell, and acting
   early forfeits the T-2h flag check, so weigh £0.1 against late team news
   and write the trade-off down. Sell prices via `Ruleset.sell_price()`.
   - **Captain = highest model projection unless PRE-DEADLINE NEWS says
     otherwise — never a recency switch.** A run of captain blanks is variance,
     not a signal: the highest-projection, highest-EO pick is a rank *shield*
     (a haul ~90% of rivals share, a blank they share too), and fading a
     blanking talisman only ever costs you the week he returns (holding Haaland
     through a 4-in-5 blank streak caught his GW14 28 and GW16 26). Show the
     top-3 EV table with ceiling/floor and the vice as the news-only fail-safe;
     do not switch the armband on form. Differential captaincy lost every week
     it was implicitly tested — take rank risk in the SQUAD, not the armband.
   - **Chip verdict every deadline (even "hold").** State it explicitly in the
     memo: name the next pre-committed window from the chip calendar
     (`/fpl-chip-strategy`), its trigger, and whether this GW meets it. Fire a
     chip only when (a) the calendar trigger is met OR (b) a written override
     shows this week beats the calendar's target on EV. The community chip
     landscape (mass-wildcard weeks, triple-captain polls, free-hit slates) is
     CONTEXT, never the trigger — discipline (calendar-driven, never impulse) is
     what makes chips a gain not a leak. Chips are the biggest untapped lever.

## Memo format (`decisions/gw{NN}.md`)

- **Header:** GW, deadline (UTC + time remaining), squad value, bank, free transfers.
- **Manager's read (write first):** the human take — team trajectory / eye-test, who's
  due/cold, the named duel(s), any brave-captain or bench-order call and its thesis. Flag
  which calls DEVIATE from the solve so the review can grade the human overlay.
- **Transfers:** OUT→IN with EV delta and rationale; hits justified against threshold.
- **XI + bench order + captain/vice:** captain EV table.
- **Chip decision:** use/hold, vs the calendar.
- **Risk table** (from news sweep) + what we're deliberately fading (the template
  deviation and why).
- **Consensus check:** one line per divergence from public projections and our
  verdict (our edge vs our miss).
- **Plan B:** the fallback if a flagged player is ruled out at T-2h.
- Commit the memo. At T-2h: re-verify flags only; if nothing changed, confirm the
  memo stands ("FINAL"); if something changed, apply Plan B, mark the edit, commit.

Never let the deadline pass without a FINAL memo — a legal recommendation from
cached data always beats silence.

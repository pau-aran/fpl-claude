# Standing transfer-path plan — living document

*Updated at every deadline BEFORE reading the optimizer proposal. Any move
(above all any hit) is checked against this first: a this-week gain that
burns the bank or FT a planned step depends on is a net loss even if the EV
gate passes it. Breaking the plan requires new information + written reason
in the decision memo.*

## State after GW10

- Bank £0.5m | **1 FT for GW11** (both banked FTs spent at GW10) | season 624
  pts (+93 vs average-manager baseline) | 1 hit taken all season
- GW10 spent BOTH FTs, no hit: Ekitiké→Mateta (the queued upgrade) +
  Ballard→Konaté (dead-slot → productive DEF). Squad now:
  Raya, Dúbravka (GK); Saliba, Calafiori, Muñoz, Senesi, **Konaté** (DEF);
  Semenyo, Szoboszlai, Mbeumo, B.Fernandes, Brooks (MID); Haaland, **Mateta**,
  Scarlett (FWD). Full 11 fit starters; bench = Dúbravka + Saliba + Brooks +
  Scarlett (real defensive cover restored via Saliba/Konaté).
- GW10 75 vs official avg 65 (+10): Haaland(C) 13→26, Konaté 8 (CS) on entry
  week, Muñoz 6, Raya 6. The Ekitiké→Mateta timing landed (Mateta entered his
  green run one GW after his ARS(A) week, as planned).
- **Ballard note:** we later confirmed (GW11 team sheets) he was NOT actually
  suspended — the ban was a mis-sourced aggregator headline (knowledge.md
  [PROCESS]). Harmless: we sold him for the productive-slot upgrade, not the ban.

## Current state — after GW17 (live snapshot)

- Bank **£1.2m** | **3 FT for GW18** (2 of 4 spent at GW17, 1 accrued) | season **1011
  pts (+135)** | 1 hit taken all season | captaincy 17/17.
- **Squad (after the GW17 AFCON reshape):** Roefs, Dúbravka (GK); Saliba, Calafiori,
  **Tarkowski**, Senesi, Konaté (DEF); B.Fernandes, **Rice**, Enzo, Szoboszlai, Brooks
  (MID); Haaland, Thiago, Mateta (FWD). Changes vs GW10: Semenyo→Enzo (GW12),
  Scarlett→Thiago + Raya→Roefs (GW13), Mbeumo→Rice + Muñoz→Tarkowski (GW17).
- Loaded on Arsenal (Saliba/Calafiori/Rice = 3, the deliberate fixture load), the
  Liverpool bloc (Konaté/Szoboszlai) and Haaland (C). Bench = Dúbravka + Saliba +
  Konaté + Brooks.
- **Live threads into GW18:** (1) B.Fernandes subbed 45' at Villa (GW17) — confirm
  fitness at the presser; (2) the fixture-blind bench-order defect (Saliba's 6 benched
  behind Tarkowski's 3 at GW17, ~−3) — now FIXED in code (`optimize()` fields the XI on
  the nearest `xpts_gw{n}` column; `start`/`bench` decision levers for reads it can't see),
  effective GW18+.

## Executed

- **GW5 — EXECUTED AS PLANNED**: FT rolled, no hit; vetoed the early
  Haaland −4 (counterfactual lost ~4 pts, reasoning PASS, reviews/gw05.md §3).
- **GW6 — EXECUTED, Haaland entry complete**: Salah→Brooks + Mheuka→Haaland
  on 2 FTs, no hit; Haaland captained at BUR(H) → 16, doubled 32; GW 55 vs
  official avg 46. Locks held (Saliba, Palmer), both vetoes graded PASS.
  The solve redirected from the memo's (infeasible) Ekitiké funding route
  to this plan's primary route — accepted via signed addendum
  (reviews/gw06.md §3–4).
- **GW7 — EXECUTED AS PLANNED: rolled the FT** → 2 banked for GW8. Refused
  the optimizer's −4 (Saliba→Timber + Palmer→Enzo): sideways fit-DEF churn +
  a phantom Palmer sale, both plan-conflicting. Captain Haaland at BRE(A) →
  goal+assist, doubled 16. GW **71 vs official avg 60 (+11)**, season 409
  (+45). Process PASS; the refused hit would have won by ~3 on an
  unforecastable Timber CB goal (reviews/gw07.md §3) — variance, not a
  regrade. First outing of the purist duel lens: all reads matchup-correct
  but none surfaced a model-underrated player yet (§4, [WATCH]).

- **GW8 — EXECUTED, forced triple-out handled cleanly.** Palmer (out 6wk),
  Gudmundsson (4wk), Brooks (2-3wk) all blanked; 2 FT → Palmer→B.Fernandes +
  Gudmundsson→Senesi, no hit, full XI restored. Vetoed Saliba→Timber (5th).
  Faded the template Saka for the crowd-sold Fernandes (value>reputation).
  Haaland(C) 26. GW **82 vs official avg 56 (+26)** — best week of the season;
  season 491 (+71). The GW6 Palmer hold-vs-sell bet resolved AGAINST the hold
  (six more weeks) but the parallel Isak-injury flip made Ekitiké a free
  starter, netting the window positive (reviews/gw08.md §2).

- **GW11 — EXECUTED AS PLANNED: rolled the FT** → 2 banked for GW12. Refused
  the optimizer's 7th Saliba→Timber churn (single-GW net +0.61, gate-flagged
  sub-threshold; lock held) and refused to chase the crowd's Liverpool sell
  (Konaté a GW10 buy, run turns GW12). Captain Haaland at LIV(H) → scored but
  MISSED A PENALTY (4, doubled 8) in a 3-0 win; correct call, unforecastable
  variance. GW **34 vs official avg 38 (−4)** — first below-average week since
  GW5, a league-wide blank slate (two in-squad pen misses); season 658 (+89).
  Process PASS; the churn veto gained 0 (vindicated 7th time). See
  reviews/gw11.md.

- **GW12 — EXECUTED: one forced injury move, refused the churn, banked the 2nd
  FT.** The Nov international break broke the week: **Semenyo OUT** (ankle, Ghana
  duty, multi-week + AFCON) and **Gabriel OUT ~4wk** (thigh, Brazil). Semenyo →
  **Enzo** (£6.7, nailed, started+scored at Burnley — a value-over-reputation buy
  of a crowd-sold, career-high-underlying mid; frees £1.3 to bank £1.8). Refused
  the 8th Saliba→Timber churn (Saliba the senior CB with Gabriel out — locked) and
  BANNED Gabriel (the optimizer's raw proposal was to BUY him — availability edge
  the model can't see). Rolled the 2nd FT (bank 2 for GW13: Semenyo timeline open,
  Senesi nearing a ban). Held the Liverpool bloc into its turned-green run (NFO
  home) — the GW11 thesis vindicated by simply not selling. Captain Haaland at
  NEW(A). See gw12.md / consensus/gw12.md.

- **GW13 — EXECUTED: the structural value reshape, 2 FT, no hit.** Scarlett →
  **Thiago** (dead-slot → Brentford's in-form No.9 v bottom-side Burnley, the
  standing plan lever) + Raya → **Roefs** (cheap-keeper downgrade to fund Thiago,
  timed to Arsenal's most depleted week — Gabriel AND Saliba both out at Chelsea).
  Locked Saliba (out on a training knock, benched — held the premium, no churn).
  Captain Haaland at home to Leeds (softest fixture, no pre-deadline doubt — he
  blanked, variance). See gw13.md / consensus/gw13.md.

- **GW14 — EXECUTED: rolled through a four-absence midweek, no hit.** Saliba (ill),
  Senesi + Brooks (5th-yellow bans), Thiago (benched at Arsenal, tactical) — all
  one-week. Refused the free cost-neutral Saliba→Virgil (lateral premium churn on a
  1-week illness); accepted a legal-but-thin 3-4-3 (benched Thiago the forced 10th)
  and banked the FT to 2. Captain Haaland → drought ended, 28; Muñoz 14. GW **69 vs
  avg 58 (+11)**; season 813 (+112). See gw14.md / consensus/gw14.md.

- **GW15 — EXECUTED: rolled 2 FT → 3, no hit.** Refused the 9th Saliba→Timber churn
  (Saliba out a 3rd week but benched, held) and the PREMATURE Mbeumo→Gakpo (Mbeumo
  available GW15-16, out only from GW17). Held Mbeumo through his soft Wolves fixture
  → 8. Captain Haaland (home to Sunderland) blanked (4th low week in 5); Fernandes 18
  carried it. GW **56 vs avg 49 (+7)**; season 869 (+119). See gw15.md.

- **GW16 — EXECUTED: rolled 3 FT → 4, no hit.** Saliba's return (3 weeks out ended)
  covered Calafiori's fresh GW16 ban with zero transfers (neat symmetry). Held Mbeumo
  for his send-off game (Man Utd got clearance to play him v BOU before AFCON).
  Refused the 3-transfer churn bundle (Saliba→Timber #10, Konaté→Gakpo, premature
  Mbeumo→Tarkowski). Captain Haaland at Palace → returned 26; Fernandes 13; Roefs 9;
  autosubs (Calafiori→Konaté 9, Muñoz→Saliba) fired. GW **72 vs avg 60 (+12)**;
  season 941 (+131). See gw16.md.

- **GW17 — EXECUTED: the AFCON reshape, 2 of 4 FT, no hit.** Mbeumo → **Rice** (the
  AFCON sale — Cameroon out from GW17; reinvested into the cheapest rider of Arsenal's
  elite GW17-24 run, £7.1 for Saka's fixtures) + Muñoz → **Tarkowski** (the injury sale
  — 0 min GW15+16, out weeks; a nailed £5.5 CB banking £0.5 to a £1.2 buffer). Locked
  Saliba (refused Saliba→Timber #11); banked the other 2 FT (→ 3 for GW18) toward the
  returnee window. Captain Haaland at home to West Ham → 32 (17/17 adherence); Rice 11
  on debut; Saliba's bench 6 stranded by the fixture-blind XI-order defect (~−3). GW
  **70 vs avg 66 (+4)**; season **1011 (+135)** — past 1000, season-high edge. See
  gw17.md / consensus/gw17.md.

## Active path — the 8-GW AFCON window (GW18 → GW24)

We are **+135 vs the average-manager baseline** and past 1000 pts; the goal is TOP 1%.
**GW18 opens with 3 FT, £1.2m bank.** The AFCON reshape (GW17) is done; the next 8-GW
tree is about **riding the loaded runs, keeping FT/bank flexibility for the returnee
window, and not churning through a low-scoring stretch** (official averages GW18-23 are
all ≤48 — the crowd is weak here, so patience compounds our edge). *(Each week's exact
call is filled at that deadline, BEFORE reading the optimizer; this is the standing map.)*

**The board we're loaded on (GW18-24 FDR):**
- **Arsenal (Saliba, Calafiori, Rice):** BHA(H)3 AVL(H)3 BOU(A)4 LIV(H)3 NFO(A)3 MUN(H)3
  LEE(A)3 — the best sustained run we hold; the triple is a deliberate fixture load. HOLD.
- **Man City (Haaland):** NFO(A)3 SUN(A)3 CHE(H)3 BHA(H)3 MUN(A)4 WOL(H)1 TOT(A)3 —
  captain anchor throughout; MUN(A)4 (GW22) the only tougher captain week (Fernandes the
  fail-safe there).
- **Liverpool (Konaté, Szoboszlai):** WOL(H)1 LEE(H)2 great GW18-19, then FUL(A)3 and
  **ARS(A)5 (GW21)** — the bloc's rough week; reassess holding it into GW21.
- **Chelsea (Enzo):** AVL(H)3 BOU(H)3 then **MCI(A)5 (GW20)** — Enzo's one hard fixture.
- **Palace (Mateta), Brentford (Thiago), Bournemouth (Senesi):** all steady 2-3 runs; HOLD.

**Week-by-week decision tree:**
- **GW18 — default ROLL (→ bank toward 4 FT), one contingency.** Good fixtures across
  the squad (Arsenal BHA(H), Liverpool WOL(H)1, City NFO). **Contingency: B.Fernandes.**
  He was subbed 45' at Villa (GW17) — if the GW18 presser confirms a knock/absence,
  he's Man Utd's now-sole premium creator and our vice, so cover him (into a nailed
  non-AFCON mid, ~£8-9; Rice/Enzo already cover the cheaper band). If he's fit, ROLL.
- **GW19 — ROLL unless a returnee/price move forces it.** Keep banking (cap 5). This is
  the low-average trough (avg ~40); patience is the edge.
- **GW20 — the Chelsea decision.** Enzo hits MCI(A)5. If the bank/FT allow and a clearly
  better-fixtured mid is available, this is the spot to move him for one week's dip — but
  only if it fits the returnee plan; otherwise hold through one hard game (he's nailed).
- **GW21 — the Liverpool-bloc decision.** Konaté/Szoboszlai hit ARS(A)5. Same test: hold
  premium through one hard fixture unless a same-price upgrade on a better run exists.
  Watch Salah's AFCON progress (Egypt) — an early exit could shorten his absence.
- **GW22-24 — the returnee window.** **Mbeumo (Cameroon) is expected back ~GW22; Salah
  (Egypt) ~GW23**, depending on how far their nations go. This is what the banked FTs
  are FOR: reassess whether a returnee (or a form player who emerged during the window)
  beats what we hold. No pre-commitment — buy the returnee only if the projection +
  fixtures beat the incumbent, not on reputation.
- **Standing FT/bank policy for the window:** bank toward 4-5 FT and keep the £1.2m
  buffer; the only "must-spend" triggers are (a) a confirmed multi-week injury to a
  starter, (b) a Fernandes absence, (c) a returnee who clearly upgrades a slot. Don't
  spend FTs on churn through the low-average trough.

**Rank discipline:** highest-EO captain (Haaland shield — landed 28/26/32 across
GW14/16/17; no recency switch, ever); ceiling via value/differentials. **Bench-order
was the #1 in-week leak** (cost ~3 again at GW17: Saliba benched behind Tarkowski) — now
FIXED in code (the optimizer fields the XI on this week's fixture column; `start`/`bench`
decision levers override for reads it can't see, e.g. a depleted opponent defence).

Chips: out of scope (but note — the AFCON disruption is the season's classic
Wildcard/Free-Hit trigger for the field; we ride it on FTs, which is the disciplined
edge if our squad stays largely intact, as it has).

## Conflicts to refuse through the AFCON window (GW18-24)

- **Buying an AFCON-bound player** before he's confirmed back — any cover/upgrade MUST
  have clean availability (no active Africa call-up).
- **Lateral premium churn** (the Saliba→Timber pattern, vetoed 11× now) — the Arsenal
  defenders are a fit, loaded hold.
- **Panic-churning through the low-average trough** (Enzo/Thiago/Mateta/the Liverpool
  bloc) after a quiet week — real new info only; the crowd is weak here, hold the runs.
- **Over-reacting to one hard fixture** (Enzo MCI-A GW20, Liverpool ARS-A GW21) — hold
  nailed premiums through a single tough game unless a genuine same-price upgrade exists.

## Watch list

- **B.Fernandes (owned, £9.3) — PRIORITY WATCH**: subbed 45' away at Villa (GW17); our
  vice and now Man Utd's sole premium creator (Mbeumo/Amad at AFCON). Confirm fitness at
  the GW18 presser — a knock/absence is the most likely GW18 forced move (cover into a
  nailed non-AFCON ~£8-9 mid).
- **Rice (new, £7.1)**: the Mbeumo AFCON replacement — nailed Arsenal mid, set-piece
  involved, on the elite GW17-24 run. Hold hard; the fixture-load anchor.
- **Tarkowski (new, £5.5)**: the Muñoz injury replacement — nailed Everton CB. Soft
  opener passed (ARS-H GW17); better fixtures BUR(A)2/NFO(A)3 ahead. Hold.
- **AFCON returnees — the window's opportunity**: **Mbeumo (Cameroon) ~GW22, Salah
  (Egypt) ~GW23** (return dates depend on tournament progress — watch results). The
  banked FTs are for reassessing these; buy back only on projection+fixtures, not name.
- **Enzo (£6.5)**: nailed Chelsea mid, career-high underlying. Hold through MCI(A)5
  (GW20) unless a same-price upgrade appears.
- **Liverpool bloc (Konaté, Szoboszlai)**: in the good run (WOL(H)1, LEE(H)2 at GW18-19);
  hold. Reassess at ARS(A)5 (GW21).
- **Muñoz (SOLD at GW17, injury)**: track only to confirm the sale doesn't need
  reversing (it shouldn't — he stayed out weeks).
- **Semenyo (SOLD to Enzo at GW12)**: calibration note — the sale's AFCON leg was softer
  than assumed (Ghana), but the injury leg + Enzo's form hold the decision; no reversal.

## Standing constraints

- Two spending FTs > one FT + one -4 (a -4 needs net ≥ 4.5 AND plan-fit).
- Keep ≥ £0.3m buffer for price-rise protection on the target path
  (bank now £1.2m — buffer restored at GW17).
- A written funding route must show its arithmetic (sells + bank ≥ buys,
  squad quota-legal) before the solve runs (GW6 lesson).
- Max 3 per club is a live constraint now (Arsenal at the cap: Saliba/Calafiori/Rice) —
  any Arsenal buy requires selling an Arsenal player first.

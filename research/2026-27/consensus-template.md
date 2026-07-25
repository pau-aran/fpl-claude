# Market Report: The 2026/27 Consensus Template and Price Dynamics

**As of:** 2026-07-25
**GW1 deadline:** 2026-08-21 17:30 UTC (18:30 BST) — 27 days out
**Data:** `db/raw/2026-07-25/bootstrap.json` (558 players, 20 clubs) + `fixtures.json`
**Registered teams at snapshot:** 1,341,561
**Author:** fpl-claude market-analysis leg

> Doctrine note. Everything below is an **input**. Where we match the crowd we do it
> deliberately (to avoid uncompensated variance), and where we deviate we do it with a
> written reason. Nothing here is an instruction.

---

## 0. Headline findings (read these first)

1. **Prices are frozen until the GW1 deadline.** Every one of the 558 players has
   `cost_change_start = 0`, `cost_change_event = 0`, `price_change_percent = "0"`, and
   `transfers_in_event = transfers_out_event = 0`. This is not a stale snapshot — it is a
   2026/27 rule change. The Premier League confirms: *"When Fantasy launches for the
   2026/27 season, all prices will be locked until the Gameweek 1 deadline on 21 August,
   at 18:30 BST."*
   ([premierleague.com](https://www.premierleague.com/en/news/4680462/whats-new-in-202627-fantasy-price-change-predictor))
   **Consequence: there is zero price urgency before 2026-08-21. Every "buy him before he
   rises" argument circulating in the community right now is void.** Our team is free
   until the deadline. This is the single most actionable fact in this report.
2. **The crowd's most-owned XI is not buildable.** Naively taking the top-owned player at
   each slot gives 4 Man City players (Haaland, Guéhi, O'Reilly, Semenyo) and costs
   £111.5m. The real template is what survives the £100m and 3-per-club constraints — and
   what survives is a **weak, cheap defence bolted to Haaland**.
3. **Haaland (£15.5m, 73.7%) + B.Fernandes (£12.0m, 47.9%) = £27.5m, 27.5% of budget, on
   two players.** That single fact determines the shape of the entire template. It is why
   38.1% of the game owns a £4.0m defender from a promoted club.
4. **Ownership is extremely concentrated.** The 50 most-owned players account for 965% of
   the 1500% total squad share — i.e. **64% of every squad slot in the game sits in 50
   players**. Top 15 alone = 32% of all slots.
5. **Arsenal have the best GW1 fixture in the league (H v Coventry, FDR 2 v 5) and the
   template can only afford one Arsenal player.** That is the cleanest structural
   mispricing on the board.

---

## 1. The template as of 2026-07-25

### 1.1 Top-owned by position (snapshot data)

**Goalkeepers**

| Player | Club | Price | Own% | 25/26 pts | 25/26 mins |
|---|---|---:|---:|---:|---:|
| Raya | ARS | £6.0m | 29.8 | 162 | 3330 |
| Dubravka | TOT | £4.0m | 24.5 | 96 | 3150 |
| Lammens | MUN | £5.0m | 19.8 | 109 | 2880 |
| Verbruggen | BHA | £4.5m | 16.1 | 130 | 3420 |
| Kinsky | TOT | £4.5m | 14.8 | 20 | 630 |
| Donnarumma | MCI | £5.5m | 11.1 | 135 | 3060 |
| Pickford | EVE | £5.5m | 9.3 | 135 | 3420 |

**Defenders**

| Player | Club | Price | Own% | 25/26 pts | 25/26 mins |
|---|---|---:|---:|---:|---:|
| Guéhi | MCI | £6.0m | 25.3 | 179 | 3150 |
| Gabriel | ARS | £8.0m | 24.8 | 209 | 2750 |
| O'Reilly | MCI | £6.5m | 24.8 | 160 | 2643 |
| Pedro Porro | TOT | £5.5m | 23.9 | 117 | 2793 |
| Diop | IPS | £4.0m | 21.4 | 31 | 812 |
| Konsa | AVL | £4.5m | 18.4 | 100 | 3035 |
| Shaw | MUN | £4.5m | 18.1 | 113 | 3220 |
| van Ewijk | COV | £4.0m | 16.7 | 0 | 0 |
| Mosquera | ARS | £5.5m | 16.0 | 40 | 986 |
| Virgil | LIV | £6.5m | 15.3 | 175 | 3420 |
| Muñoz | CRY | £5.5m | 13.1 | 136 | 2400 |
| Lacroix | CRY | £6.0m | 12.9 | 154 | 3085 |
| Senesi | TOT | £6.0m | 12.7 | 175 | 3288 |
| N.Williams | NFO | £5.0m | 12.0 | 128 | 3203 |
| Calafiori | ARS | £5.5m | 11.9 | 109 | 1697 |
| Tarkowski | EVE | £6.0m | 10.8 | 170 | 3330 |
| Spence | TOT | £4.5m | 10.5 | 78 | 2049 |

**Midfielders**

| Player | Club | Price | Own% | 25/26 pts | 25/26 mins |
|---|---|---:|---:|---:|---:|
| B.Fernandes | MUN | £12.0m | 47.9 | 235 | 3065 |
| Szoboszlai | LIV | £7.0m | 40.9 | 160 | 3232 |
| Rogers | CHE | £7.5m | 34.8 | 169 | 3280 |
| Rice | ARS | £7.5m | 22.5 | 184 | 3093 |
| Semenyo | MCI | £8.5m | 20.2 | 202 | 3200 |
| Ndiaye | EVE | £6.0m | 20.1 | 128 | 2781 |
| Kroupi Jr | BOU | £7.5m | 15.2 | 113 | 1663 |
| Cunha | MUN | £8.0m | 14.9 | 143 | 2493 |
| Mbeumo | MUN | £8.0m | 13.5 | 148 | 2611 |
| Palmer | CHE | £9.5m | 13.4 | 114 | 1954 |
| Gibbs-White | NFO | £8.0m | 13.2 | 188 | 3101 |
| Anderson | MCI | £6.5m | 12.5 | 180 | 3332 |
| Wirtz | LIV | £7.5m | 12.2 | 125 | 2374 |
| Saka | ARS | £9.5m | 11.2 | 157 | 2218 |
| Sarr | CRY | £6.5m | 11.0 | 117 | 2173 |
| Cherki | MCI | £7.5m | 10.2 | 135 | 1772 |

**Forwards**

| Player | Club | Price | Own% | 25/26 pts | 25/26 mins |
|---|---|---:|---:|---:|---:|
| Haaland | MCI | £15.5m | 73.7 | 239 | 2953 |
| João Pedro | CHE | £7.5m | 47.2 | 177 | 2658 |
| Brobbey | SUN | £6.0m | 21.3 | 92 | 1920 |
| Thiago | BRE | £8.0m | 17.7 | 181 | 3282 |
| Calvert-Lewin | LEE | £6.0m | 17.5 | 142 | 2721 |
| Gyökeres | ARS | £7.5m | 14.7 | 128 | 2217 |
| Watkins | AVL | £8.0m | 13.1 | 167 | 2833 |
| Isak | LIV | £9.0m | 12.7 | 41 | 694 |
| Kusi-Asare | FUL | £4.5m | 8.2 | 6 | 49 |

### 1.2 The costed template squad

Method: MILP (pulp/CBC) over the snapshot — **maximise total `selected_by_percent`**
subject to the real game constraints (£100.0m, 2/5/5/3, max 3 per club). This is the
squad the crowd's own preferences produce once you make them legal. XI then chosen as the
highest-ownership valid 11 inside it.

**TEMPLATE SQUAD — £100.0m exactly, £0.0m bank, 3-4-3**

| | Pos | Player | Club | Price | Own% |
|---|---|---|---|---:|---:|
| XI | GKP | Raya | ARS | £6.0m | 29.8 |
| XI | DEF | Guéhi | MCI | £6.0m | 25.3 |
| XI | DEF | Pedro Porro | TOT | £5.5m | 23.9 |
| XI | DEF | Diop | IPS | £4.0m | 21.4 |
| XI | MID | B.Fernandes | MUN | £12.0m | 47.9 |
| XI | MID | Szoboszlai | LIV | £7.0m | 40.9 |
| XI | MID | Rogers | CHE | £7.5m | 34.8 |
| XI | MID | Ndiaye | EVE | £6.0m | 20.1 |
| XI | FWD | **Haaland (C)** | MCI | £15.5m | 73.7 |
| XI | FWD | João Pedro | CHE | £7.5m | 47.2 |
| XI | FWD | Brobbey | SUN | £6.0m | 21.3 |
| BEN | GKP | Dubravka | TOT | £4.0m | 24.5 |
| BEN | DEF | Konsa | AVL | £4.5m | 18.4 |
| BEN | DEF | van Ewijk | COV | £4.0m | 16.7 |
| BEN | MID | Hughes | CRY | £4.5m | 9.6 |

- **Starting XI cost: £83.0m. Bench cost: £17.0m. Squad: £100.0m, zero in the bank.**
- Aggregate ownership of the 15: **455.5** points of share; of the XI: **386.3**.
- Club counts: CHE 2, MCI 2, TOT 2, and one each of ARS/AVL/COV/CRY/EVE/IPS/LIV/MUN/SUN.

**Read this squad honestly: the crowd is fielding a £15.5m striker behind a
£15.5m back three.** Guéhi, Porro and Diop start. Gabriel (the highest-scoring defender
in the game last season), O'Reilly, Rice, Semenyo and Saka are all *priced out* of the
Haaland build. That is the template's structural weakness and the most obvious place for
a differentiated build to attack.

### 1.3 The alternative structure: the no-Haaland build

26.3% of the game does not own Haaland. Re-running the same optimisation with Haaland
banned shows exactly what that money buys — and it is a completely different shape:

**NO-HAALAND TEMPLATE — £99.5m, 5-4-1**

| | Pos | Player | Club | Price | Own% |
|---|---|---|---|---:|---:|
| XI | GKP | Raya | ARS | £6.0m | 29.8 |
| XI | DEF | Guéhi | MCI | £6.0m | 25.3 |
| XI | DEF | Gabriel | ARS | £8.0m | 24.8 |
| XI | DEF | O'Reilly | MCI | £6.5m | 24.8 |
| XI | DEF | Pedro Porro | TOT | £5.5m | 23.9 |
| XI | DEF | Diop | IPS | £4.0m | 21.4 |
| XI | MID | B.Fernandes | MUN | £12.0m | 47.9 |
| XI | MID | Szoboszlai | LIV | £7.0m | 40.9 |
| XI | MID | Rogers | CHE | £7.5m | 34.8 |
| XI | MID | Rice | ARS | £7.5m | 22.5 |
| XI | FWD | João Pedro | CHE | £7.5m | 47.2 |
| BEN | GKP | Dubravka | TOT | £4.0m | 24.5 |
| BEN | MID | Ndiaye | EVE | £6.0m | 20.1 |
| BEN | FWD | Brobbey | SUN | £6.0m | 21.3 |
| BEN | FWD | Calvert-Lewin | LEE | £6.0m | 17.5 |

XI cost £77.5m, bench £22.0m. Note it upgrades **five** slots (Gabriel, O'Reilly, Rice,
plus a real fifth defender and a stronger bench) for the price of one striker. The
trade-off is stark and quantifiable: **you are betting ~£8m of squad quality against
Haaland's captaincy ceiling.**

---

## 2. Price radar

### 2.1 The radar is empty — and that is the finding

Direct extraction from the snapshot across all 558 players:

| Field | Min | Max | Non-zero count |
|---|---:|---:|---:|
| `cost_change_start` | 0 | 0 | **0 / 558** |
| `cost_change_event` | 0 | 0 | **0 / 558** |
| `transfers_in_event` | 0 | 0 | **0 / 558** |
| `transfers_out_event` | 0 | 0 | **0 / 558** |
| `transfers_in` | 0 | 0 | **0 / 558** |
| `price_change_percent` | "0" | "0" | distinct values = `{"0"}` |

Nobody has risen. Nobody has fallen. Nobody *can* until 2026-08-21 17:30 UTC.

Cross-checks:
- **LiveFPL price predictions** (`https://www.livefpl.net/prices`) returns **no prediction
  data** at this date — consistent with a frozen market, not with a fetch failure of
  meaningful content.
- **Official Premier League:** prices "locked until the Gameweek 1 deadline on 21 August,
  at 18:30 BST."
  ([premierleague.com](https://www.premierleague.com/en/news/4680462/whats-new-in-202627-fantasy-price-change-predictor))
- **Fantasy Football Scout** on the mechanism: changes are ±£0.1m at a time, capped at
  £0.3m per gameweek per player, and — new this season — occur at **00:00 UK time**
  instead of the old 01:30/02:30.
  ([FFScout, 2026-07-20](https://www.fantasyfootballscout.co.uk/2026/07/20/how-do-fpl-price-changes-work))
- **Contradicted claim.** Fantasy Football Fix published "Szoboszlai & Kroupi Jr Rise,
  Gordon Falls" with Szoboszlai at £7.1m
  ([source](https://www.fantasyfootballfix.com/blog-index/fpl-price-changes-szoboszlai-kroupi-jr-rise-gordon-falls/)).
  Our snapshot has Szoboszlai at **£7.0m with `cost_change_start = 0`**, and the official
  rule says no pre-season changes. Treat that article as either a modelled projection or
  stale 2025/26 content — **not** a live price. **[UNVERIFIED / likely wrong]**

### 2.2 What replaces the old edge

FPL has shipped an **official Price Change Predictor** for 2026/27: a page tracking each
player's progress toward a change, refreshed every 15 minutes, with "Very Likely to Rise"
/ "Likely to Drop" labels, surfaced on player profiles, team selection and transfers
pages ([premierleague.com](https://www.premierleague.com/en/news/4680462/whats-new-in-202627-fantasy-price-change-predictor);
[FFScout](https://www.fantasyfootballscout.co.uk/2026/07/21/fpl-2026-27-price-change-predictions)).

**Moneyball implication:** price-change foreknowledge was, for a decade, an edge held by
the minority who used LiveFPL / FPL Statistics. FPL has now given it to all 1.34m+
managers for free. **That edge is dead as of 2026/27** — we should not build process
around it, and we should expect faster, sharper herd movement on rises now that the
signal is universal. Our edge must come from minutes and xPts, not from beating the
crowd to a £0.1m.

### 2.3 The pricing that already happened (the reveal, 2026-07-22)

Since in-season movement is frozen, the only "price dynamics" available pre-deadline are
the **reveal-vs-last-season deltas**. Per FFScout's price-reveal coverage
([reveals live](https://www.fantasyfootballscout.co.uk/2026/07/22/fpl-2026-27-price-reveals-live-haaland-rises-to-record-high);
[9 first impressions](https://www.fantasyfootballscout.co.uk/2026/07/23/fpl-2026-27-9-first-impressions-of-the-player-prices)):

**Risers (the market's own repricing)**

| Player | New price | Change | Note |
|---|---:|---:|---|
| Haaland | £15.5m | +£1.5m | Record high for any FPL player; 239 pts in 25/26 |
| B.Fernandes | £12.0m | +£3.0m | Joint-biggest rise; 235 pts, 9 goals **24 assists** |
| Kroupi Jr | £7.5m | +£3.0m | Joint-biggest rise; also reclassified MID (one of 11 position changes) |
| Gabriel | £8.0m | +£2.0m | Highest DEF price since TAA 23/24; 22 DefCon pts |
| Thiago | £8.0m | +£2.0m | 181 pts |
| Senesi | £6.0m | +£1.5m | Pure DefCon repricing |
| Raya | £6.0m | +£? | First £6.0m keeper in five years |
| Tarkowski | £6.0m | +£0.5m | DefCon |

**Fallers**

| Player | New price | Change | Note |
|---|---:|---:|---|
| Isak | £9.0m | **-£1.5m** | 694 PL mins in 25/26 (snapshot); fibula fracture + ankle surgery |
| Gyökeres | £7.5m | -£0.5m | 128 pts / 2217 mins |
| Foden | £7.0m | -£? | Cheapest since 2020/21 |

Note the structural consequence FFScout flags: **only Haaland is priced above £9.0m among
forwards**, and **no defender at Coventry, Hull or Ipswich costs more than £4.0m** — 46
defenders sit at the £4.0m floor, over half from the three promoted clubs
([FFScout £4.0m defender guide](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed)).
That floor is what makes the Haaland template affordable at all.

### 2.4 Our post-deadline pressure watchlist (predictive, not observed)

These are **our** projections of who moves first once the freeze lifts on 21 August, based
on ownership momentum plus GW1 fixture. **[UNVERIFIED — forward-looking]**

- **Likeliest early risers:** Arsenal attacking/defensive assets (H v Coventry, FDR 2 v 5
  — the best GW1 fixture in the league); Haaland (H v Bournemouth); João Pedro if Chelsea
  return at Fulham.
- **Likeliest early fallers:** van Ewijk (£4.0m, 16.7%) and Diop (£4.0m, 21.4%) if either
  is not in the GW1 XI — 38.1% of the game is exposed to two unconfirmed starters;
  Szoboszlai (40.9%) if Liverpool's opener at Newcastle goes badly under a new manager;
  Kinsky/Dubravka, whichever loses the Spurs gloves.

---

## 3. Community consensus

### 3.1 Rules and structure context for 2026/27

- **DefCon survives unchanged.** Defensive contribution points stay exactly as introduced
  in 2025/26 — 10 combined CBIT for defenders, no new milestone tiers, despite community
  lobbying
  ([premierleague.com](https://www.premierleague.com/en/news/4361991/whats-happening-with-defensive-contribution-points-in-202627-fantasy)).
- **Chips:** two full sets (Wildcard, Free Hit, Triple Captain, Bench Boost), one set per
  half. Confirmed independently by the snapshot's `chips` array, which lists each chip
  twice.
- **No Assistant Manager chip.**
- **BPS reworked** to reduce overlap with DefCon — intended to improve bonus potential for
  goalkeepers, full-backs, attacking midfielders and forwards
  ([FFScout, 5 rule changes](https://www.fantasyfootballscout.co.uk/2026/07/20/fpl-2026-27-5-rule-changes-new-features-announced)).
  *This is under-discussed and it matters:* it partly undoes the 2025/26 centre-back bonus
  bonanza and pushes value back toward attacking full-backs.
- **Live rank/mini-league updates and 20-minute provisional bonus** are new.
- **11 position changes**, headlined by Kroupi Jr moving to midfield at £7.5m.

### 3.2 Popular structures

- **3-4-3 is the de facto Haaland structure**, and our optimisation confirms it is what the
  budget forces. Community write-ups pitch **3-5-2** as the recommended GW1 shape, with a
  four-defender setup "viable if defensive prices are kind and DEFCON remains in place"
  ([Onside cheat sheet](https://onsidearena.com/tips/fpl-cheat-sheet-2026-27)) **[UNVERIFIED
  — unvetted source]**.
- **"Big at the back" / 5-at-the-back** is being actively drafted (e.g. Timber, Virgil,
  Gvardiol, Calafiori, Aina builds) but it is fundamentally a **no-Haaland structure** —
  see §1.3. You cannot run five real defenders and a £15.5m striker.
- **Single premium forward is the near-universal answer.** Because only Haaland exceeds
  £9.0m among forwards, the "double premium forward" debate of past seasons has largely
  evaporated; the second forward slot is a £6.0-8.0m question (João Pedro 47.2%, Brobbey
  21.3%, Thiago 17.7%, Calvert-Lewin 17.5%).
- **The £4.0m defender enabler is doctrine this year.** With 46 defenders at the floor,
  every mainstream draft carries two or three. FFScout's own ranking of the bracket puts
  **Bobby Thomas (COV)** first — "centre-back potential with goal-scoring threat from set
  plays, 8.56 defensive contributions per 90" — and **Aurele Amenda (COV)** at 8.97 DC/90,
  with **van Ewijk (COV)** framed as an assist play ("46 chances created, 8 assists in the
  Championship")
  ([FFScout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed)).
  The crowd has bought van Ewijk (16.7%) far ahead of the two players the reference site
  rates higher.

### 3.3 The "essential" list

By ownership, only two players clear 40% and are treated as genuinely essential in
community discourse:

1. **Haaland (73.7%)** — the near-consensus "you cannot go without him". The argument
   cited repeatedly: top-scoring player after the first six gameweeks in **all four** of
   his City seasons; 239 pts / 27 goals / 8 assists in 2025/26; Norway did not play at the
   2026 World Cup so **no tournament fatigue** — a meaningful discriminator in a
   post-World-Cup season; and City have two home fixtures against promoted clubs inside
   the opening seven
   ([premierleague.com](https://www.premierleague.com/en/news/4680490)).
2. **B.Fernandes (47.9%)** — the consensus vice-captain and the default premium mid.

Second tier of "hard to be without": João Pedro (47.2%), Szoboszlai (40.9%), Rogers
(34.8%), Raya (29.8%).

### 3.4 GW1 captain consensus

**Haaland, effectively unanimous.** One aggregator puts him at **56% captaincy with Bruno
Fernandes as vice**, describing him as the "Tier-1 default"
([Onside](https://onsidearena.com/tips/fpl-cheat-sheet-2026-27)) **[UNVERIFIED — unvetted
source; treat the 56% as indicative only]**. The fixture supports it: **MCI (H) v BOU**,
FDR 3 for City against Bournemouth's 5.

The only credible alternative captains in GW1 by fixture are **Arsenal assets at home to
Coventry** (ARS FDR 2, COV FDR 5 — the largest differential on the GW1 slate) and **Bruno
Fernandes away at Hull** (MUN FDR 2).

### 3.5 What the crowd is reacting to (transfer market context)

The 2026 summer window reshaped the pool materially, and much of the current ownership is
a direct response ([NBC Sports](https://www.nbcsports.com/soccer/news/premier-league-transfers-for-summer-2026-list-of-every-in-and-out-for-each-club),
[Squawka](https://www.squawka.com/en/features/premier-league-transfers-confirmed-2026-summer-window/)):

- **Mohamed Salah left Liverpool** (contract terminated, departed 1 July) after nine years
  ([Liverpool FC](https://www.liverpoolfc.com/news/mohamed-salah-leave-liverpool-end-season)).
  Liverpool also lost Konaté and Robertson. **Andoni Iraola replaced Arne Slot as head
  coach** ([Liverpool FC](https://www.liverpoolfc.com/news/liverpool-fc-appoint-andoni-iraola-new-head-coach)).
  Szoboszlai's 40.9% is the crowd's answer to "who replaces Salah's points" — snapshot
  confirms he is Liverpool's **direct free-kick #1 and penalty #2** (Isak is pen #1).
- **Morgan Rogers → Chelsea for £118.7m**, the window's biggest known fee — and he joined
  on **2026-07-21, four days before this snapshot**.
- **Semenyo and Guéhi joined Man City in January 2026**; **Elliot Anderson** is City's
  record summer signing from Forest.
- **Senesi, Van Hecke, Robertson, Tonali and Dubravka all joined Tottenham**; Vicario and
  Kinsky are still there.

---

## 4. Where we think the crowd is wrong

### 4.1 Overrated

**1. Dubravka (TOT, £4.0m, 24.5%) — and the whole Spurs goalkeeper guess.**
He is **37 years old** (born 1989-01-15), joined Tottenham on 2026-07-01, and Spurs
already have Vicario (£4.5m) and Kinsky (£4.5m). The snapshot shows **24.5% on Dubravka
plus 14.8% on Kinsky = 39.3% of the entire game guessing at an unresolved three-way
goalkeeper battle**, purely because Dubravka is the cheapest apparently-playing keeper in
the game. This is a pure enabler chase with no minutes evidence. And because prices are
frozen, **there is no cost whatsoever to waiting for pre-season minutes** before
committing. The crowd has taken an unnecessary risk for a reward that does not exist this
year.
*Our read:* Verbruggen (BHA, £4.5m, 16.1%) played **3420 minutes** for 130 points — 28.9
pts per £m, second-best keeper value in the game — and his job is not in question. Paying
£0.5m more to remove a genuine minutes risk is the correct trade in a season where the
£0.1m game is neutered.

**2. Morgan Rogers (CHE, £7.5m, 34.8%).**
34.8% ownership on a player who **signed for Chelsea four days before this snapshot** and
has never played a competitive minute for them. His 169 points and 3280 minutes were as
Aston Villa's undisputed creative focal point. At Chelsea he enters a queue containing
Palmer (£9.5m, **Chelsea penalty #1**), João Pedro, Estêvão, Quenda, Enzo and Caicedo. The
snapshot shows Rogers on **no Chelsea set pieces at all** — no penalties, no direct
free-kicks. The crowd has priced the Villa role and bought the Chelsea shirt. Classic
reputation transfer.
*Additionally:* Chelsea's GW1-5 run is middling (FDR 15) and includes **Arsenal away with
a difficulty of 5** in GW3.

**3. The £4.0m promoted-club defender block: van Ewijk (COV, 16.7%) + Diop (IPS, 21.4%).**
Combined **38.1%** of the game on two defenders with **0 and 812 Premier League minutes
respectively last season**. Neither is a confirmed starter. Worse, **Coventry have the
joint-worst opening run in the league** (GW1-5 FDR 17: Arsenal away at difficulty 5, Man
City away at difficulty 5). And the reference site itself ranks two *other* Coventry
defenders — Bobby Thomas and Aurele Amenda, on 8.56 and 8.97 defensive contributions per
90 — ahead of van Ewijk for DefCon purposes
([FFScout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed)).
The crowd picked the name it had heard, not the profile that scores.
*Moneyball rule 2 applies directly: most FPL points lost are lost to benchings.*

**4. B.Fernandes (MUN, £12.0m, 47.9%).**
The **joint-biggest price rise in the game (+£3.0m)** for a season built on **24 assists**
against 9 goals. Assists are the single least repeatable line in FPL — they depend on
teammates' finishing, which regresses hard. He is 31 (born 1994-09-08) and at £12.0m he
must reproduce ~6.7 points per game to justify the tag. Combined with Haaland he
consumes 27.5% of the budget and *is the direct cause* of the template's £4.0m-defender
problem. We are not saying he is bad; we are saying **£12.0m is the market pricing the
best-case repeat of an unrepeatable assist season**, and 47.9% is the crowd agreeing
without argument.

**5. Mosquera (ARS, £5.5m, 16.0%).**
Owned as the beneficiary of Saliba's absence — the snapshot confirms **Saliba is flagged
`i`, "Back injury — Unknown return date", and has collapsed to 0.5% ownership**. But
Arsenal signed **Piero Hincapié from Leverkusen** (£5.5m, 5.7% owned, 1787 minutes last
season) for exactly that vacancy. Two players, same price, same job; Mosquera has 986
career PL minutes and Hincapié has near double. The crowd is backing the cheaper-known
name 3:1 on no evidence.

**6. Brobbey (SUN, £6.0m, 21.3%).**
92 points from 1920 minutes is **3.0 points per game** — below replacement for a starting
£6.0m forward. He is **not** Sunderland's penalty taker (the snapshot has Diarra at pen
#1). Sunderland's GW1-5 includes Arsenal at home and Man City away. 21.3% ownership is
"cheapest forward who might start", which is a price argument, not a points argument.

### 4.2 Underrated

**1. ~~Ekitiké (LIV, £7.5m, 0.2%) — the sharpest asymmetry on the board.~~ RETRACTED.**

> **MANAGER'S CORRECTION (2026-07-25, written on merge).** This entry is **wrong and must
> not be acted on.** Ekitiké has a **ruptured Achilles**: the same snapshot this report was
> built from carries `status: i`, `chance_of_playing_next_round: 0`, news *"Achilles injury
> — Expected back 31 Dec"*. `research/2026-27/fitness-returners.md` sources it independently
> (ruptured v PSG in mid-April, 8.5–12 month programme, rehabbing in LA, realistic return
> band Jan–Apr 2027, Iraola: *"not close"*), and the transfer leg reached the same
> conclusion separately. He is not a free option; he is a dead squad slot for at least half
> the season, and the 0.2% ownership is the market pricing him **correctly**, not missing
> something.
>
> The defect is process, not arithmetic: the case was built entirely from last season's
> points-per-minute and never read the availability fields sitting in the same row. That is
> the exact failure mode Moneyball rule #2 exists to prevent — *minutes are the market
> inefficiency*. **Standing rule reaffirmed: no player enters a shortlist without a minutes
> check first.** Retained here rather than deleted so the review can grade the miss.

The salvageable half of the argument: **Isak (£9.0m, 12.7%)** is coming off a season of
**694 Premier League minutes** wrecked by a fibula fracture and ankle surgery that cost him
22 games ([This Is Anfield](https://www.thisisanfield.com/2026/05/alexander-isak-scary-experience-challenging-liverpool-season/)),
under a **new manager in Iraola** whose Bournemouth sides pressed high and rotated forwards.
That durability question is real and should be priced into any Isak buy — but it does **not**
imply a backup route, because Liverpool's backup route is injured until 2027.

**2. The Arsenal GW1 block — the template's structural blind spot.**
Arsenal host **Coventry at home in GW1 with an FDR of 2 against Coventry's 5** — the
largest difficulty gap on the entire opening slate. And the Haaland template can afford
exactly **one** Arsenal player (Raya). Gabriel (£8.0m) scored **209 points, the most of any
defender in the game**, and is only 24.8% owned. Rice (£7.5m, 22.5%) scored 184 points, is
**Arsenal's direct free-kick #1**, and played 3093 minutes. Saka (£9.5m, 11.2%) is
**Arsenal's penalty #1** at 11% ownership. The crowd is not avoiding these players on
merit; it is avoiding them because it spent £27.5m on two men.

**3. Truffert (BOU, £5.5m, 4.9%) — the best points-per-million defender in the game.**
165 points from **3378 minutes** at £5.5m = **30.0 pts per £m**, the joint-highest of any
player with 1500+ minutes on 2026/27 prices. Owned by 4.9%. Bournemouth's GW1-5 is the
league's hardest (FDR 18), which is precisely why he is cheap and unowned — but he is a
season-long value anchor and, with prices frozen, **we lose nothing by tracking him and
buying when the run turns.** Same bracket: **Van Hecke (TOT, £5.0m, 8.1%, 29.6 pts/£m,
3210 mins)** and **Mitchell (CRY, £4.5m, 7.4%, 30.0 pts/£m, 3253 mins)**.

**4. Elliot Anderson (MCI, £6.5m, 12.5%) — the efficient way to own City's midfield.**
180 points from **3332 minutes** (near ever-present) at £6.5m = 27.7 pts/£m. City's record
signing, walking into a first-team midfield role. The crowd prefers **Semenyo at £8.5m
(20.2%)** — £2.0m more for 202 points in comparable minutes. Given the **3-per-club cap is
the binding constraint at Man City** (Haaland + Guéhi + O'Reilly + Semenyo + Anderson +
Donnarumma + Cherki + Doku all have double-digit or near-double-digit interest), the
£2.0m saved by taking Anderson over Semenyo is what unlocks Gabriel or Rice elsewhere.

**5. Enzo (CHE, £7.0m, 5.1%) — buy the proven Chelsea role, not the new one.**
157 points, **3114 minutes**, and **0.54 expected goal involvements per 90 — the highest
xGI/90 of any midfielder under 6% ownership in the entire dataset**. He is £0.5m cheaper
than Rogers and his Chelsea role is a known quantity, whereas Rogers' is four days old. If
you want Chelsea midfield exposure, the crowd has bought the wrong end of it by a factor
of seven in ownership.

**6. Honourable mentions the market has forgotten.**
- **Garner (EVE, £6.0m, 3.7%)** — 159 pts from **3413 minutes**, 26.5 pts/£m. Currently
  flagged `i` (groin, expected back 22 Aug) which is exactly why he's cheap and unowned;
  one day after the GW1 deadline. Watch, don't buy yet.
- **Foden (MCI, £7.0m, 5.1%)** — cheapest since 2020/21, 0.47 xGI/90. Blocked only by the
  City 3-cap.
- **Kelleher (BRE, £5.0m, 5.7%)** and **Petrović (BOU, £4.5m, 3.7%)** — 3330 and 3420
  minutes, 28.6 and 27.6 pts/£m. Solved goalkeepers at Dubravka-adjacent prices.
- **Harry Wilson (LEE, £6.5m, 9.8%)** — 168 pts, **0.36 xGI/90**, moved to Leeds who have
  a soft GW1-5 (FDR 14).

### 4.3 Where we should simply match the crowd

Discipline cuts both ways. We see no argument against:

- **Haaland at 73.7%.** The captaincy ceiling is real, the 26.3% of the field who fade him
  are taking uncompensated downside in a gameweek where he is home to Bournemouth, and no
  tournament fatigue is a genuine 2026-specific edge in his favour. Owning him is not a
  crowd-follow; it is the correct read that happens to be popular.
- **João Pedro at £7.5m / 47.2%.** 177 points, 2658 minutes, at a price that leaves the
  build flexible. Fair.
- **Raya at £6.0m.** Expensive for a keeper, but 162 points and 3330 minutes behind
  Arsenal's defence with the league's best GW1 fixture is defensible.

---

## 5. Open questions for the rest of the team

1. **Tottenham goalkeeper.** Dubravka vs Kinsky vs Vicario is 39.3% of the game's exposure
   and is unresolved. This is the highest-value single piece of team news between now and
   the deadline. → news sweep.
2. **Rogers' Chelsea role and set-piece duties.** He is on nothing at present per the
   snapshot. If he takes corners or plays as a nailed 10, 34.8% is correct and we should
   match; if not, it is the biggest single fade available.
3. **Iraola's Liverpool shape.** Szoboszlai at 40.9% is a bet on a role under a manager
   who has never picked a Liverpool team. Also determines Ekitiké/Isak.
4. **Arsenal centre-back.** Saliba out indefinitely; Mosquera (16.0%) vs Hincapié (5.7%).
5. **Do Coventry/Ipswich actually start van Ewijk and Diop?** 38.1% exposure, zero
   evidence.

---

## Sources

- FPL API snapshot: `db/raw/2026-07-25/bootstrap.json`, `fixtures.json` (2026-07-25)
- [Premier League — What's new in 2026/27 Fantasy: Price Change Predictor](https://www.premierleague.com/en/news/4680462/whats-new-in-202627-fantasy-price-change-predictor)
- [Premier League — Haaland handed a RECORD price for 2026/27 Fantasy](https://www.premierleague.com/en/news/4680490)
- [Premier League — What's happening with defensive contribution points in 2026/27](https://www.premierleague.com/en/news/4361991/whats-happening-with-defensive-contribution-points-in-202627-fantasy)
- [FFScout — How do FPL price changes work? (2026-07-20)](https://www.fantasyfootballscout.co.uk/2026/07/20/how-do-fpl-price-changes-work)
- [FFScout — 5 rule changes + new features announced (2026-07-20)](https://www.fantasyfootballscout.co.uk/2026/07/20/fpl-2026-27-5-rule-changes-new-features-announced)
- [FFScout — Price change predictions coming (2026-07-21)](https://www.fantasyfootballscout.co.uk/2026/07/21/fpl-2026-27-price-change-predictions)
- [FFScout — Price reveals live: Haaland rises to record high (2026-07-22)](https://www.fantasyfootballscout.co.uk/2026/07/22/fpl-2026-27-price-reveals-live-haaland-rises-to-record-high)
- [FFScout — FPL 2026/27 is live (2026-07-23)](https://www.fantasyfootballscout.co.uk/2026/07/23/fantasy-premier-league-fpl-2026-27-is-live)
- [FFScout — 9 first impressions of the player prices (2026-07-23)](https://www.fantasyfootballscout.co.uk/2026/07/23/fpl-2026-27-9-first-impressions-of-the-player-prices)
- [FFScout — Best £4.0m defenders for 2026/27: all 46 assessed (2026-07-24)](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed)
- [FFScout — Best value FPL players: last season's points, 2026/27 prices (2026-07-25)](https://www.fantasyfootballscout.co.uk/2026/07/25/best-value-fpl-players-last-seasons-points-with-2026-27-prices)
- [FFScout — Ultimate pre-season guide 2026/27](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more)
- [LiveFPL price changes](https://www.livefpl.net/prices) — no prediction data at 2026-07-25
- [NBC Sports — Premier League transfers summer 2026, every in and out](https://www.nbcsports.com/soccer/news/premier-league-transfers-for-summer-2026-list-of-every-in-and-out-for-each-club)
- [Squawka — Every confirmed PL transfer, 2026 summer window](https://www.squawka.com/en/features/premier-league-transfers-confirmed-2026-summer-window/)
- [Liverpool FC — Salah to leave at end of season](https://www.liverpoolfc.com/news/mohamed-salah-leave-liverpool-end-season)
- [Liverpool FC — Iraola appointed head coach](https://www.liverpoolfc.com/news/liverpool-fc-appoint-andoni-iraola-new-head-coach)
- [This Is Anfield — Isak on his injury-hit Liverpool season](https://www.thisisanfield.com/2026/05/alexander-isak-scary-experience-challenging-liverpool-season/)
- [Fantasy Football Hub — Ultimate Guide to GW1 2026/27](https://www.fantasyfootballhub.co.uk/fantasy-premier-league-ultimate-guide-fpl-tips) (paywalled)
- **[UNVERIFIED, unvetted]** [Onside — FPL Cheat Sheet 2026/27](https://onsidearena.com/tips/fpl-cheat-sheet-2026-27) (source of the 56% captaincy figure)
- **[UNVERIFIED, contradicted]** [Fantasy Football Fix — price changes article](https://www.fantasyfootballfix.com/blog-index/fpl-price-changes-szoboszlai-kroupi-jr-rise-gordon-falls/)

*Reproducibility note: the template and no-Haaland squads in §1.2/§1.3 are MILP solutions
(pulp/CBC) maximising summed `selected_by_percent` over the 2026-07-25 snapshot subject to
£100.0m, 2/5/5/3 and max-3-per-club. Both solve to a unique optimum.*

# 2026 Summer Transfer Window — FPL Intelligence

**Compiled:** 2026-07-25 · **GW1 deadline:** 2026-08-21 17:30 UTC
**Data baseline:** `db/raw/2026-07-25/bootstrap.json` (558 players, 20 teams)
**Window:** opened Mon 15 June 2026, closes Tue 1 September 2026 23:00 BST — **five weeks of squad churn remain after this document.**

**Method.** Every player in the snapshot with `team_join_date >= 2026-06-01` was extracted (56 records), cross-checked against
published confirmed-deal lists, and each material mover was researched for role, minutes and set-piece duty. FPL's
`penalties_order` / `corners_and_indirect_freekicks_order` / `direct_freekicks_order` fields were dumped league-wide and
compared to news. Sources are cited inline; anything not corroborated by a named outlet is marked **[UNVERIFIED]**.

---

## 0. Read this first: the window happened alongside a managerial earthquake

**Eight of twenty clubs have a new manager.** Any minutes model trained on 2025/26 usage is materially wrong for these clubs,
and several of the transfers below only make sense in light of the new coach. This is the single biggest overlay of the season.

| Club | 2026/27 manager | New? | Tactical note for FPL |
|---|---|---|---|
| Liverpool | **Andoni Iraola** | NEW | 4-2-3-1, high press. Big departure from Slot. |
| Chelsea | **Xabi Alonso** | NEW | 4-2-3-1 in early friendlies; back-three (3-4-2-1 / 3-4-3) also trialled |
| Man City | **Enzo Maresca** | NEW | Guardiola gone after a decade; midfield reset around Anderson |
| Tottenham | **Roberto De Zerbi** | NEW | **3-4-3 / 3-4-2-1** — wing-backs, three CBs. Drives the entire Spurs window |
| Nott'm Forest | **Oliver Glasner** | NEW | Glasner is a 3-4-2-1 coach — wing-back upside at Forest |
| Crystal Palace | **Pierre Sage** | NEW | Glasner's replacement; system not yet proven |
| Fulham | **Alvaro Arbeloa** | NEW | Replaces Marco Silva |
| Bournemouth | **Marco Rose** | NEW | Replaces Iraola |
| Ipswich | **Gary O'Neil** | NEW | Promoted-side manager; back-five likely |
| Arsenal (Arteta), Villa (Emery), Brentford (Andrews), Brighton (Hurzeler), Coventry (Lampard), Everton (Moyes), Hull (Jakirovic), Leeds (Farke), Man Utd (Carrick), Newcastle (Howe), Sunderland (Le Bris) | — | returning | |

Source: [premierleague.com — Manager line-up complete for 2026/27](https://www.premierleague.com/en/news/4679012) ·
[ESPN — PL giants hit managerial reset](https://www.espn.com/soccer/story/_/id/48937196/premier-league-giants-hit-managerial-reset-capitalize)

---

## 1. Summary table — the ~46 moves that matter

Price = FPL 2026/27 price from the 25 July snapshot. `Sel%` = ownership at snapshot.
Minutes confidence: **High** = expected first-choice; **Med** = starts-or-rotates; **Low** = squad filler / backup.

### Premium & mid-price attackers

| Player | New club | FPL pos | Price | Sel% | Expected role | Minutes | Set-piece notes | Source |
|---|---|---|---|---|---|---|---|---|
| **Morgan Rogers** (from AVL, £117m) | CHE | **MID** | 7.5 | 34.8% | Left-side / No.10 in Alonso's 4-2-3-1. Chelsea's record signing and joint-2nd-priciest FPL asset | **High** on paper — but **misses much of pre-season** (post-World Cup holiday). Ease into GW1 | **None in FPL data.** Palmer stays pens #1; Enzo #2, Estêvão #3. Rogers gets no dead balls at Chelsea, unlike Villa | [Sky](https://www.skysports.com/football/news/11095/13564944/morgan-rogers-transfer-news-chelsea-complete-record-breaking-lb117m-deal-to-sign-forward-from-aston-villa) · [Chelsea FC](https://www.chelseafc.com/en/news/article/morgan-rogers-signs-for-chelsea) · [Roundtable](https://roundtable.io/sports/soccer/premier-league/chelsea/news/revealed-when-morgan-rogers-will-join-xabi-alonso-chelsea-squad-in-pre-season) |
| **Elliot Anderson** (from NFO, £116m — British record) | MCI | MID | 6.5 | 12.5% | Central to Maresca's midfield "from the moment competitive football returns". Ball-carrier/presser replacing Bernardo Silva's role | **High** | None in FPL data. City pens: Haaland 1, Marmoush 2, Semenyo 3, Doku 4. Anderson is not a City dead-ball option | [Sky](https://www.skysports.com/football/news/11095/13558090/elliot-anderson-to-man-city-midfielder-completes-record-breaking-lb116m-transfer-from-nottingham-forest) · [Read Man City](https://readmancity.com/2026/07/06/elliot-anderson-record-city-move-maresca-midfield-test/) |
| **Christos Tzolis** (Club Brugge, £34m) | ARS | MID | 6.5 | 1.0% | Direct **Trossard replacement**. Left wing or No.10. 22 G + 29 A in all comps 2025/26; **most assists of any player in Europe's top 10 leagues (23)** | **Med** — rotation with Martinelli/Madueke/Eze behind Saka. Already in pre-season camp | None. Arsenal pens Saka 1 / Gyökeres 2 / Ødegaard 3; corners Rice+Saka; DFK Rice 1, Saka 2, Eze 3 | [Sky](https://www.skysports.com/football/news/11670/13564283/arsenal-transfer-news-christos-tzolis-signs-in-lb34m-deal-from-club-brugge-as-replacement-for-leandro-trossard) · [PL](https://www.premierleague.com/en/news/4680629/an-output-machine-why-tzolis-is-ideal-replacement-for-trossard-at-arsenal) |
| **Alejandro Garnacho** (CHE, **loan** w/ obligation) | AVL | MID | 6.0 | 1.0% | Straight into **Rogers' vacated left-wing minutes**. Speed and directness | **Med-High** — the minutes exist; the finishing is the question | None | [Sky](https://www.skysports.com/football/news/11677/13566210/alejandro-garnacho-transfer-news-aston-villa-offer-winger-route-to-redemption-after-completing-chelsea-exit) · [Read Aston Villa](https://readastonvilla.com/2026/07/22/how-unai-emery-can-unlock-alejandro-garnacho-at-aston-villa/) |
| **Johan Manzambi** (Freiburg, ~£50-59.5m) | AVL | MID | 6.0 | 3.6% | Replaces **Rogers' central qualities** — the No.10 role, not the wing | **Med-High** | None | [Read Aston Villa](https://readastonvilla.com/2026/07/22/how-unai-emery-can-unlock-alejandro-garnacho-at-aston-villa/) · [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Harry Wilson** (Fulham, **free**) | LEE | MID | 6.5 | **9.8%** | Left-footed right winger — Farke's stated priority. Can play centrally | **High** | **Best set-piece news of the window.** Regular dead-ball taker at Fulham (scored a FK v Brighton last season); Leeds previously relied on right-footed Stach. **FPL data shows Wilson with NO set-piece order — stale** | [Yorkshire Post](https://www.yorkshirepost.co.uk/sport/football/leeds-united-stephen-warnock-harry-wilson-fulham-8810493) · [Yorkshire Evening Post](https://www.yorkshireeveningpost.co.uk/sport/football/leeds-united/leeds-united-transfers-harry-wilson-stats-8779562) |
| **Bazoumana Touré** (Hoffenheim, £42-43m) | NEW | MID | 6.0 | 0.2% | Explicitly bought to replace **Anthony Gordon** on the left. 5 G + 12 A in 30 Bundesliga games aged 20 | **Med** — 20-year-old, Howe eases players in; but the minutes are genuinely vacant | None. NEW pens: Woltemade 1, Osula 2, Bruno G. 3, Wissa 4 (FPL data) | [Sports Mole](https://www.sportsmole.co.uk/football/newcastle-united/transfer-talk/news/newcastle-confirm-gbp42-5m-signing-of-gordon-replacement-wanted-by-liverpool_600728.html) · [OneFootball](https://onefootball.com/en/news/newcastle-land-highly-rated-winger-bazoumana-toure-43100926) |
| **Víctor Muñoz** (Osasuna, £34.5-35m) | LIV | MID | 6.5 | 0.9% | Left-sided attacker in Iraola's **4-2-3-1**, alongside Wirtz behind Isak. Liverpool **hijacked Newcastle** for him | **Med** — **missed the start of pre-season** (extended post-World Cup break, won it with Spain). Not on the US tour initially | None | [Read Liverpool](https://readliverpoolfc.com/articles/victor-munoz-andoni-iraola-liverpool-shortcut/) · [TNT Sports](https://www.tntsports.co.uk/football/premier-league/2026-2027/liverpool-pre-season-tracker-victor-munoz-reds-andoni-iraola-first-season_sto23321682/story.shtml) · [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Mateus Fernandes** (West Ham, £85m — Spurs club record fee at the time) | TOT | MID | 6.0 | 5.0% | Box-to-box central midfielder alongside Tonali. Age 21 | **High** — no World Cup, full pre-season, already scoring in friendlies | None yet. Spurs pens: Solanke 1, Kudus 2, Xavi Simons 3, Richarlison 4 (**and Simons is out until 31 Dec** — see §3) | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) · [PL Briefing](https://www.premierleague.com/en/news/4680841/the-briefing-salibas-injury-blow-fernandes-scores-spurs-screamer-and-more) |
| **Sandro Tonali** (Newcastle, £100m) | TOT | MID | 5.5 | 3.0% | "The midfield conductor Spurs have been missing" — deep-lying CM in De Zerbi's 3-4-3 | **High** — no World Cup, full pre-season | **FPL data gives him corners #10 and DFK #4 — effectively nothing.** Do not buy him for set pieces | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) |
| **Youri Tielemans** (AVL, £35m) | MUN | MID | 6.0 | 1.0% | Part of United's central-midfield overhaul under Carrick | **Med** — and **flagged: hamstring, 75%** in FPL | **FPL gives him pens #3** behind Bruno Fernandes (1) and Mbeumo (2) — i.e. no realistic pen equity | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Andrey Santos** (CHE, £48m) | MUN | MID | 5.0 | 1.6% | Deep midfielder. United still shopping for **one more** No.6 (Koné/Baleba) — his ceiling depends on that | **Med → Low** if Koné or Baleba lands | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [Sky](https://www.skysports.com/football/news/11667/13566243/man-utd-transfer-news-manu-kone-and-carlos-baleba-strongly-considered-in-search-for-third-midfielder-signing) |
| **Jaidon Anthony** (Burnley, ~£15m) | BRE | MID | 6.0 | 0.3% | Wide attacker; "on target" in friendlies | **Med** | None | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Abdul Fatawu** (Leicester) | IPS | MID | 5.5 | 0.3% | Right winger — FFS bill him as "the Championship's top shooter" | **Med-High** | None in FPL. IPS pens: Clarke 1, Philogene 2, Hirst 3 | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Loum Tchaouna** (Burnley, ~£20m) | COV | MID | 5.5 | 0.1% | Wide attacker for promoted Coventry | **Med** | None. COV pens: Wright 1, Torp 2, Grimes 3 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Tyrique George** (CHE loan→permanent, ~£18m) | EVE | MID | 5.5 | 0.1% | Wide forward under Moyes | **Low-Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Hayden Hackney** (Middlesbrough, ~£16-25m) | EVE | MID | 5.5 | 0.3% | Central midfield | **Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Merlin Röhl** (Freiburg, ~£18m) | EVE | MID | 5.0 | 0.1% | Central midfield depth | **Low-Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **João Gomes** (Wolves, £34-38m) | AVL | MID | 5.5 | 0.3% | Ball-winning No.6. FFS flag him explicitly as a **DefCon** asset ("will he keep gaining FPL DefCon points?") | **High** | None. AVL pens Buendía 1, Watkins 2 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Xaver Schlager** (RB Leipzig, **free**) | NFO | MID | 5.0 | 0.1% | Central midfield under new boss Glasner | **Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Sean Steur** (Ajax, £23m) | NEW | MID | 5.0 | 0.1% | Teenage midfielder — development signing | **Low** | None | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Frank Onyeka** (loan→permanent) | COV | MID | 5.0 | 0.2% | Midfield | **Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Geovany Quenda** (Sporting CP, ~£40m) | CHE | MID | 5.5 | 0.1% | **Signed as a wing-back**, FPL classifies him **MID** — a cheap route to attacking returns *if* Alonso plays a back three. FFS themselves ask "wing-back or winger?" | **Low-Med** — and **flagged (unspecified injury, 75%)**; omitted from the pre-season tour squad | None | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) · [Roundtable](https://roundtable.io/sports/soccer/premier-league/chelsea/news/chelsea-suffer-injury-blows-as-two-summer-signings-omitted-from-pre-season-squad) |
| **Oscar Zambrano** (Maribor) | HUL | MID | 4.5 | 0.7% | Promoted-side midfield | **Low-Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Zadok Yohanna** (AIK, ~£21.5m) | BHA | MID | 5.0 | 0.1% | Brighton's usual buy-young-and-wait profile | **Low** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Jeremy Monga** (Leicester) | MCI | MID | 5.0 | 0.0% | Teenage development signing | **Low** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |

### Forwards

| Player | New club | FPL pos | Price | Sel% | Expected role | Minutes | Set-piece notes | Source |
|---|---|---|---|---|---|---|---|---|
| **Emmanuel Emegha** (Strasbourg, capt.) | CHE | FWD | 5.0 | 0.5% | Competing with Delap **and** N. Jackson to be João Pedro's backup. Scored twice in early friendlies | **Low** — **flagged (hamstring, 75%)** and **left out of the Australia tour squad**. Pedro's place "is guaranteed" | CHE pens: Palmer 1, Enzo 2, Estêvão 3, Delap 4 | [SI](https://www.si.com/soccer/six-chelsea-players-need-to-impress-preseason-2026) · [CaughtOffside](https://www.caughtoffside.com/2026/07/24/chelsea-lose-latest-striker-signing-to-injury/) |
| **Emersonn** (Toulouse, ~£26m) | IPS | FWD | 5.5 | 0.4% | Ipswich's marquee striker signing | **Med-High** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Chuba Akpom** (Ajax, ~£7m) | IPS | FWD | 5.0 | 0.5% | Rotational striker / support | **Low-Med** | IPS pens: Hirst 1, Clarke 2, Philogene 3 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Álvaro Rodríguez** (Elche, ~£25.7m) | BOU | FWD | 6.0 | 0.3% | Striker depth behind Evanilson under **new manager Marco Rose** | **Low-Med** | BOU pens: Kroupi 1, Kluivert 2, Tavernier 3 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Callum Wilson** (West Ham, **free**) | BRE | FWD | 5.5 | 0.4% | Reserve forward behind Igor Thiago (£8.0m, 17.7% owned) | **Low** | BRE pens: Thiago 1, Schade 2, Jensen 3 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Jonah Kusi-Asare** (Bayern Munich, ~£5.2m) | FUL | FWD | **4.5** | **8.2%** | Teenage striker at a **£4.5m FWD price** under new boss Arbeloa — the ownership is pure price-point speculation, not a minutes read. FFS call him a "youth option" | **Low** — **this is the single most over-owned unproven asset in the game** | None. FUL pens: Robinson 1 (a defender), Iwobi 2 | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |

### Defenders and goalkeepers

| Player | New club | FPL pos | Price | Sel% | Expected role | Minutes | Set-piece notes | Source |
|---|---|---|---|---|---|---|---|---|
| **Marcos Senesi** (Bournemouth, **free**) | TOT | DEF | 6.0 | **12.7%** | Central CB of De Zerbi's back three. Possession-focused | **High** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) |
| **Jan Paul van Hecke** (Brighton, £52m) | TOT | DEF | 5.0 | 8.1% | Right-sided CB of the back three; "one of the best ball-playing CBs in Europe" | **High** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) |
| **Andy Robertson** (Liverpool, **free**) | TOT | DEF | **4.5** | 1.8% | **Left wing-back** in a 3-4-3, tipped as likely captain. Competes with Destiny Udogie | **Med-High** — age 32 is the risk, not the role | None listed; Porro is Spurs' DFK #1 and corners #6 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) |
| **Piero Hincapié** (Leverkusen loan → **permanent**, ~£34.5m) | ARS | DEF | 5.5 | 5.7% | Left CB / LB. **Saliba out for an "extended period"; Timber and White both flagged** — the door is wide open | **Med-High**, rising | None | [SI](https://www.si.com/soccer/arsenal-crushing-cristhian-mosquera-injury-timeline-william-saliba-absence-continues) · [Sky — Saliba](https://www.skysports.com/football/news/11670/13566125/william-saliba-injury-arsenal-confirm-france-international-will-miss-extended-period-after-returning-from-world-cup-with-back-problem) |
| **Marco Palestra** (Atalanta, £47m) | CHE | DEF | 5.5 | 1.7% | **Named best defender in Serie A last season.** Alonso "personally requested" him; Palestra rejected Inter to come. Attacking **wing-back** classified DEF | **Med** — the block is Reece James (£5.5m, 8.1% owned). One report says James stays at RB; another has James moving to CM or RCB, which would hand Palestra the flank | CHE corners: James 5, Neto 6; DFK James 1 | [PL](https://www.premierleague.com/en/news/4676428/marco-palestra-who-is-chelseas-new-full-back-and-why-did-they-sign-him) · [Roundtable](https://roundtable.io/sports/soccer/premier-league/chelsea/players/xabi-alonso-maps-out-reece-james-new-role-after-chelseas-signing) |
| **Luka Vuskovic** (Tottenham, £46-50m) | BHA | DEF | 5.0 | 2.2% | FFS: "six-goal centre-half" — genuine aerial goal threat | **Med-High** | BHA DFK: Dunk 3, De Cuyper 4; corners Groß 5 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) · [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Pascal Struijk** (Leeds, ~£20m) | BHA | DEF | 5.0 | 0.5% | CB competing with Dunk/Vuskovic/Wieffer | **Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Jérémy Jacquet** (Rennes, £55m) | LIV | DEF | 5.0 | 2.0% | CB signed to succeed the departed Konaté | **Med-High** — but **flagged (shoulder, 75%)** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Tarik Muharemovic** (Sassuolo, ~£34.1m) | LEE | DEF | 5.0 | 0.7% | CB — Leeds' response to losing Struijk | **Med-High** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Issa Diop** (Fulham, ~£8.5m) | IPS | DEF | **4.0** | **21.4%** | Right-sided CB. 173 top-flight PL games, **but only nine league starts since March 2025.** Must beat club captain Dara O'Shea, who was ever-present last season. A back five would fit all three CBs in | **Med — genuinely uncertain.** Buy for the price point and DefCon, not for a guaranteed start | Career DefCon 6.67–9.79 per 90; lower possession at Ipswich should raise volume | [FFScout — Diop](https://www.fantasyfootballscout.co.uk/2026/07/23/4-0m-fpl-defender-diop-could-see-more-defcon-points-at-ipswich) |
| **Óscar Mingueza** (Celta Vigo, **free**) | CRY | DEF | 4.5 | 0.1% | Full-back / wing-back. Palace are selling Lacroix (see §3) and are short at the back | **Med**, rising | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Thomas Meunier** (Lille, **free**) | SUN | DEF | 4.5 | 0.6% | Right-back/wing-back. FFS ask the right question: "what does it mean for **Mukiele** (£5.5m, 8.6% owned)?" | **Med** — a direct threat to a popular budget pick | SUN corners: Xhaka 4, Hume 5 | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Matt Targett** (Newcastle, **free**) | HUL | DEF | 4.0 | 1.2% | Experienced LB for a promoted side | **Med-High** | HUL: Giles corners 4, DFK 1 | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Cédric Kipré** (Reims, ~£2.2m) | IPS | DEF | 4.0 | 0.4% | CB depth | **Low** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Aurèle Amenda** (Eintracht Frankfurt, ~£17m) | COV | DEF | 4.0 | 0.5% | CB for promoted Coventry | **Med** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Jannik Schuster** (RB Salzburg, ~£12m) | BRE | DEF | 4.5 | 0.1% | Defensive depth | **Low** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Costinha** (Olympiacos, ~£11m) | BHA | DEF | 4.5 | 0.1% | Depth | **Low** | None | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |
| **Michael Svoboda** (Venezia) | BHA | DEF | 5.0 | 0.1% | Depth | **Low** | None | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Martin Dúbravka** (Burnley, **free**) | TOT | GKP | **4.0** | **24.5%** | **Backup.** TeamTalk's predicted XI names **Antonín Kinský (£4.5m, 14.8% owned)** as Spurs' No.1. Vicario (£4.5m) also still on the books | **Low — by design.** At £4.0m he is the game's premier non-playing bench enabler. Anyone rostering him as a starter has misread it | — | [TeamTalk](https://www.teamtalk.com/tottenham-hotspur/starting-eleven-2026-2027-season-six-new-additions-complete-formation-change) · FPL snapshot |
| **Jack Butland** (Rangers, ~£3m) | HUL | GKP | 4.5 | 1.2% | Likely No.1 for promoted Hull, over Phillips (£4.0m, 2.7% owned) | **Med-High** | — | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Illan Meslier** (Leeds, **free**) | ARS | GKP | 5.0 | 0.1% | Backup to Raya (£6.0m — the first £6.0m GK since 2021/22) | **Low** | — | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Karl Darlow** (Leeds, **free**) | MUN | GKP | 4.5 | 0.1% | Third-choice behind Lammens (£5.0m, 19.8%). **Flagged, 75%** | **Low** | — | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Kayne van Oevelen** (Volendam) | IPS | GKP | 4.5 | 0.2% | Competing with Walton (£4.5m) and Palmer (£4.0m, 6.7% owned) | **Low-Med** | — | [ESPN](https://www.espn.com/soccer/story/_/id/48955344/premier-league-2026-summer-transfers-all-confirmed-ins-outs-every-club) |
| **Ewen Jaouen** (Reims, ~£18.5m) | NEW | GKP | 4.5 | 0.1% | Backup to Pope | **Low** | — | [FFScout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) |

---

## 2. Departures freeing up value

The purest Moneyball edge in a transfer window is not the arrival — it is the **vacated minutes, penalties and set pieces** the market hasn't repriced yet.

### Tier 1 — reshapes a whole team's point distribution

| Departure | Club | Gone to | Vacated | Beneficiary |
|---|---|---|---|---|
| **Mohamed Salah** | LIV | Left on a free; **still an unsigned free agent** as of late July | ~Everything: right wing, penalties, direct free kicks, corners | **The entire Liverpool attack is repriced.** FPL now lists **Isak pens #1**, Szoboszlai #2, Gakpo #3, Wirtz #4, Mac Allister #5; Szoboszlai takes DFK #1 and corners #4. **FFS and FPL disagree here — see §3.** Szoboszlai at £7.0m with 40.9% ownership is the market's answer |
| **Anthony Gordon** | NEW | Barcelona, ~£60.5-69.3m | Left wing, ~2,500 mins | Bazoumana Touré (£6.0m) directly; Elanga and Barnes (both £6.0m) also gain |
| **Morgan Rogers** | AVL | Chelsea, £117m | Left wing + No.10, Villa's chief creator | **Garnacho takes the wing, Manzambi takes the middle.** Watkins (£8.0m, **cut to £8.0m after a -£1.0m drop**) loses his primary supplier |
| **Elliot Anderson** | NFO | Man City, £116m | Forest's engine room | Gibbs-White (£8.0m, 13.2%) becomes even more central under Glasner; Hutchinson/Sangaré/Schlager split the minutes |
| **Sandro Tonali** | NEW | Tottenham, £100m | Newcastle central midfield | Bruno Guimarães (£7.0m, 8.4%) — already NEW's corners #6 and DFK #2, now unchallenged |
| **Marc Cucurella** | CHE | Real Madrid, £51.8m | Chelsea left-back / left of a back three | Colwill, Gusto, and whoever Alonso installs on the left. **Chelsea's LB slot is genuinely open** |
| **Ibrahima Konaté** | LIV | Real Madrid, **free** | Liverpool starting CB | Jacquet (£5.0m) was bought for it; Gomez and Van Dijk (£6.5m, 15.3%) absorb the rest |

### Tier 2 — meaningful minutes freed

| Departure | Club | Vacates | Beneficiary |
|---|---|---|---|
| **Leandro Trossard** → Beşiktaş | ARS | Rotation wide/No.10 minutes | Tzolis (£6.5m), Martinelli, Madueke |
| **Bernardo Silva** → Real Madrid (free) + **John Stones** released + **Akanji** → Inter + **Aké** → Fenerbahçe | MCI | Midfield and an entire defensive tier | Anderson in midfield; **Guehi (£6.0m, 25.3%), O'Reilly (£6.5m, 24.8%)** and Gvardiol now form a settled back line — the market has already piled in |
| **Rasmus Højlund** → Napoli + **Casemiro** → Inter Miami + **Sancho** released + **Onana** → Trabzonspor (loan) | MUN | Striker, midfield, GK | Šeško (£7.0m, flagged 75%), Tielemans/Andrey Santos, **Lammens (£5.0m, 19.8%)** now uncontested in goal |
| **Andy Robertson** → Tottenham (free) | LIV | Liverpool left-back | Kerkez (£5.5m, 6.6%) — now unchallenged |
| **Jan Paul van Hecke** → Tottenham | BHA | Brighton starting CB | Vuskovic and Struijk, both arriving £5.0m |
| **Marcos Senesi** → Tottenham (free) | BOU | Bournemouth CB | Hill (£5.5m), Diakité, Milosavljević under new boss Rose |
| **Idrissa Gueye** + **Seamus Coleman** released | EVE | Midfield and RB | Hackney, Röhl, Iroegbunam; O'Brien at full-back |
| **Illan Meslier** + **Karl Darlow** both left | LEE | **Leeds have exactly ONE goalkeeper (Perri, £4.5m) in the FPL data — and Perri is being sold to Torino** | James Trafford — see §3 |
| **Kieran Trippier** → Wolves (free) + **Matt Targett** released | NEW | Newcastle full-back depth | Livramento (flagged), Hall (£5.0m, 4.8%) |
| **Youri Tielemans** → Man Utd | AVL | Villa central midfield | João Gomes, Manzambi, Barkley |
| **Harry Wilson** + **Issa Diop** + **Raúl Jiménez** all left | FUL | Fulham set pieces, a CB slot and striker cover | **Fulham's dead balls are now thin: Robinson (a DEF) is pens #1, Iwobi pens #2 and corners #1.** Muñiz (£5.5m) has less competition up top |
| **Luka Vuskovic** → Brighton + **Bissouma**, **Dragusin**, **Lankshear** all out | TOT | Squad churn under De Zerbi | The six new arrivals |

---

## 3. Data vs news conflicts

This is the section that pays. Six categories of divergence, ordered by how much money they can cost.

### 3.1 CONFIRMED/AGREED DEALS NOT YET IN THE FPL DATA — the traps

A player still priced at his old club will be **removed or repriced**, and any transfer you make into him is burnt.

| Player | FPL snapshot says | Reality as of 2026-07-25 | Severity |
|---|---|---|---|
| **Maxence Lacroix** | **CRY, DEF, £6.0m, 12.9% owned** | **Chelsea agreed a ~£51-52m deal; personal terms fully agreed; medical set for Friday.** Sky Sports reported the agreement | 🔴 **CRITICAL.** 12.9% of the game owns a Palace defender who is joining Chelsea. Expect a reprice/re-team before GW1. Do not buy Lacroix as a Palace asset |
| **James Trafford** | **MCI, GKP, £5.0m, 1.0% owned** | **Leeds' No.1 target; Man City want £40m; Newcastle pulled out; Leeds "optimistic of signing this weekend" / confident "within 24 hours".** FFS's price piece already assumes it: *"Leeds expect James Trafford (£5.0m)"* | 🔴 **HIGH — but as an opportunity.** A £5.0m keeper who is City's third choice becomes **Leeds' undisputed No.1** (Meslier and Darlow gone, Perri sold to Torino). Watch for the reclassification |
| **Daizen Maeda** | **ABSENT from FPL entirely** | **Ipswich confirmed the signing from Celtic today (25 July), ~£10m, deal to 2029.** Ipswich's fifth signing of the summer; 79 goals in 212 Celtic games | 🟠 A likely Ipswich starter with zero FPL price yet. Watch which position FPL assigns him |
| **Hidemasa Morita** | **ABSENT** | Confirmed to **Hull City** from Sporting CP on a free (ESPN) | 🟡 Promoted-side midfielder |
| **Modou Keba Cissé** | **ABSENT** | Confirmed to **Aston Villa** from LASK (~£4m per FFS) | 🟡 Depth |
| **Aladji Bamba** | **ABSENT** | Confirmed to **Newcastle** from Monaco | 🟡 Depth |
| **Rodrigo Rêgo** | **ABSENT** | Confirmed to **Brighton** from Benfica | 🟡 Depth |
| **Denner** (~£6.7m) / **Dastan Satpaev** | **ABSENT** | Both confirmed to **Chelsea** (Corinthians / Kairat Almaty) | 🟡 Depth/youth |
| **Samuel Martínez**, **Ifeanyi Ndukwe** (~£2.6m) | **ABSENT** | Confirmed to **Liverpool** (Atlético Nacional / Austria Wien) | 🟡 Youth |
| **Tynan Thompson** | **ABSENT** | Confirmed **Tottenham → Man Utd** | 🟡 Youth |

### 3.2 A DEPARTED PLAYER STILL IN THE FPL DATA

| Player | FPL says | Reality |
|---|---|---|
| **Diego Coppola** | **BHA, DEF, £4.5m, `team_join_date: null`** | ESPN lists him as **sold to Paris FC**. The null join date is itself a data smell. Treat as **gone** — do not select |
| **Nicolás Uche** | CRY, FWD, £5.0m, `status: u` | FPL has correctly flagged this one: *"has returned to Getafe CF"*. Included for completeness — the `u` status is the tell |

**Credit where due:** the FPL dataset is otherwise *clean* on departures. Salah, Cucurella, Trossard, Konaté, Gordon, Højlund, Akanji, Bernardo Silva, Stones, Aké, Trippier, Jiménez, Gueye, Kiwior, Casemiro, Sancho, André Onana, Bissouma, Drăgușin, Malen, Barrenechea, Milner, March, Webster, Veltman, Gruda, Sarmiento, Murić, Boly, Ortega and Gunn are all **absent**. Only Coppola slipped through.

### 3.3 STALE SET-PIECE FIELDS — every summer signing has blank dead-ball orders

**Not one of the 56 new joiners has a `corners_and_indirect_freekicks_order` or `direct_freekicks_order` except Tonali** (corners 10, DFK 4 — i.e. nothing), **and only Tielemans has a `penalties_order` (3, behind Bruno and Mbeumo).**

This is systematically stale, not informative. The FPL API is showing last season's assignments carried over. The concrete casualty:

- **Harry Wilson (LEE, £6.5m, 9.8% owned)** shows **no set-piece order at all**, yet reporting is explicit that he was a regular Fulham dead-ball taker and that his **left foot fills a gap Leeds did not previously have** (they leaned on right-footed Anton Stach). FPL's data currently gives Stach corners #4 and DFK #1. **Expect Wilson to take over some or all of that.** This is an un-priced edge.
- Conversely: do **not** assume Rogers inherits Chelsea dead balls (Palmer is entrenched), Anderson inherits City's (Haaland/Marmoush), or Tonali inherits Spurs' (he is 10th on corners).

### 3.4 THE SET-PIECE SOURCE ITSELF IS STALE

Fantasy Football Scout's [set-piece takers page](https://www.fantasyfootballscout.co.uk/fantasy-premier-league-set-piece-takers) is stamped **"last verified GW31"** — i.e. *before* the window. It still lists **Xavi Simons** as a Spurs penalty and free-kick taker (he is injured until 31 December), and **Semenyo** as a City free-kick taker only. **Neither the FPL API nor FFS is currently a reliable set-piece source.** Re-verify from pre-season friendly footage and the first pressers.

**Direct conflict worth resolving before GW1:**

| Question | FPL API says | FFS / press says |
|---|---|---|
| **Who takes Liverpool's penalties post-Salah?** | **Isak #1**, Szoboszlai #2, Gakpo #3 | FFS lists **Szoboszlai, Gakpo, Mac Allister** — Isak not listed. FFS's price article calls Szoboszlai *"a potential penalty-taking successor to Salah"* |
| Who takes Man City's penalties? | Haaland 1, Marmoush 2, **Semenyo 3**, Doku 4 | FFS: Haaland, Marmoush, Doku, Matheus Nunes — **Semenyo omitted from pens** |

Szoboszlai is 40.9% owned at £7.0m; Isak is 12.7% at £9.0m. **The market has priced in Szoboszlai-as-penalty-taker. The API disagrees.** Resolving this is worth real points and should be the first item in the pre-deadline news sweep.

### 3.5 POSITIONAL CLASSIFICATION QUIRKS

| Player | FPL pos | Reality | Why it matters |
|---|---|---|---|
| **Morgan Rogers** | **MID £7.5m** | Signed and described as a **forward** by Chelsea and Sky; 169 FPL points last season; joint-top for shots among midfielders | Attacker output on the midfield scoring table (5 pts/goal, clean-sheet point) at the same price as João Pedro the striker. The 34.8% ownership says the market has spotted it |
| **Eli Junior Kroupi** | **MID £7.5m** (BOU) | **Reclassified from FWD to MID**, and repriced **+£3.0m** — the joint-largest rise in the game alongside Bruno Fernandes. 13 goals in 33 PL games. Bournemouth's **penalties #1** | Not a transfer, but the single biggest classification change of the window. See §3.6 |
| **Geovany Quenda** | **MID £5.5m** (CHE) | Signed **as a wing-back** (both FFS and Chelsea coverage describe him that way) | If Alonso plays a back three, a £5.5m MID plays wing-back — cheap attacking-return route. Currently injury-flagged, so this is a watch, not a buy |
| **Marco Palestra** | **DEF £5.5m** (CHE) | Attacking **wing-back**, best defender in Serie A last season | Classic wing-back-as-DEF value — *if* he displaces Reece James |
| **Andy Robertson** | **DEF £4.5m** (TOT) | **Left wing-back** in De Zerbi's 3-4-3 | A £4.5m attacking wing-back at a club playing three at the back is the cheapest attacking-defender route in the game |
| **Antoine Semenyo** | **MID £8.5m** (MCI) | Joined City in the **January 2026** window, not this summer | See §3.6 |
| **Bazoumana Touré**, **Jaidon Anthony**, **Tyrique George**, **Fatawu**, **Tchaouna** | all **MID** | all wide **forwards** | Standard FPL winger-as-MID value; nothing exotic, but it stacks with fixture runs |

### 3.6 CORRECTIONS TO THE BRIEFING PREMISE

Two moves widely described as summer-2026 business are **not** in this window, per `team_join_date`:

- **Alexander Isak → Liverpool: `team_join_date = 2025-09-01`.** He joined in the *2025* window and, per reporting, *"played so little in his debut campaign"* that he is effectively a new signing — but he is not a 2026 arrival. At £9.0m and 12.7% owned, with **Ekitiké out until 31 December (Achilles)**, Isak has **no competition whatsoever** for Liverpool's centre-forward minutes.
- **Antoine Semenyo → Man City: `team_join_date = 2026-01-09`.** A *January* signing. 2026/27 is his first full season at City, priced £8.5m, 20.2% owned.
- Also worth disambiguating: **"Muñoz → Liverpool" is Víctor Muñoz** (MID, £6.5m, from Osasuna). **Daniel Muñoz remains at Crystal Palace** (DEF, £5.5m, 13.1% owned). Two different players; the FPL IDs are the only safe join key.
- **Marc Guehi** (MCI, £6.0m, 25.3% owned) also joined in **January 2026** (`2026-01-19`), not this summer.

### 3.7 INJURY FLAGS ON NEW SIGNINGS (all from the snapshot's `news` field)

| Player | Club | Flag |
|---|---|---|
| Youri Tielemans | MUN | Hamstring, 75% |
| Geovany Quenda | CHE | Unspecified, 75% — **omitted from the pre-season tour squad** |
| Emmanuel Emegha | CHE | Hamstring, 75% — **not travelling to Australia** |
| Jérémy Jacquet | LIV | Shoulder, 75% |
| Karl Darlow | MUN | Unspecified, 75% |

And the **non-signing** injuries that reshape where the new arrivals' minutes come from:

| Player | Club | Status | Consequence |
|---|---|---|---|
| **William Saliba** | ARS | Back, **no return date** — "extended period" after a World Cup injury | Hincapié, Mosquera (16.0% owned), Calafiori all gain |
| **Jurriën Timber** / **Ben White** | ARS | both "expected back **21 Aug**" — i.e. the **GW1 deadline day itself** | Arsenal's back line is a GW1 minefield |
| **Hugo Ekitiké** | LIV | **Achilles, back 31 Dec** | Isak has a monopoly on Liverpool CF minutes |
| **Xavi Simons** | TOT | **Knee, back 31 Dec** | Removes Spurs' pens #3 / corners #8 / DFK #2. Kudus (also flagged 75%), Maddison and Tel absorb it |
| **Dejan Kulusevski** | TOT | Knee, no return date | |
| **Wilson Odobert** | TOT | Knee, back 21 Nov | Spurs' attack is thin — which is why De Zerbi says business is *"not finished yet"* |
| **Benjamin Šeško** | MUN | Shin, 75% | |
| **Kaoru Mitoma** | BHA | Hamstring, no return date | |
| **Rodri** | MCI | Back, no return date | Anderson's minutes look even safer |
| **James Garner** | EVE | Groin, back **22 Aug** | Everton's corners #4 / DFK #1 misses GW1 |

### 3.8 STILL-OPEN SITUATIONS TO MONITOR — **[UNVERIFIED]**

| Situation | Status | FPL relevance |
|---|---|---|
| **Man Utd's third midfielder: Manu Koné (Roma) or Carlos Baleba (Brighton)** | Deal in principle agreed with Koné's representatives, ~€50m bid planned; Romano reports Baleba is *ready* to move but no club-to-club contact yet. **United intend to sign only one** | Directly caps **Andrey Santos'** minutes. A Baleba exit also thins Brighton's midfield |
| **Tottenham striker: Kroupi or Vlahović** | **Bournemouth have flatly refused to sell Kroupi** (contract to 2030, owner not entertaining offers) despite an £80m Spurs willingness. Vlahović is the free-agent fallback at ~£150k/week | If Kroupi *did* move, a £7.5m MID with BOU's pens #1 and 15.2% ownership would be repriced mid-window. **Currently reads as safe — but re-check weekly.** De Zerbi has confirmed Spurs' business is not finished |
| **Crystal Palace's Lacroix replacement** | Linked with Raphaël Le Guen (Brest) and Chrislain Matsima (Augsburg). Palace also enquired about Disasi, who is not keen | Palace's back line — Munoz (13.1%), Mitchell (7.4%), Richards — faces a rebuilt partnership. Clean-sheet projections should be marked down until settled |
| **Mohamed Salah's destination** | Still an **unsigned free agent**; listed among summer 2026 free agents alongside Goretzka and Vlahović. One FFS line calls him "retired" — **that appears to be an error** | If he signs for a PL club before 1 September, FPL adds a new asset mid-window |
| **Cristhian Mosquera injury reports** | Some outlets carried a "crushing Mosquera injury timeline" headline; the only concrete timeline traceable is his **December 2025** ankle injury. **FPL currently lists him `status: a` (fit)** | He is **16.0% owned at £5.5m** and a primary beneficiary of Saliba's absence. Verify at the first Arsenal presser |
| **Window still has five weeks to run** | Closes 1 September, i.e. **after GW1 and GW2** | Any GW1 squad will need at least one in-window correction. Budget a free transfer for it |

---

## 4. Top 10 FPL-relevant conclusions

1. **Lacroix is the trap of the window.** 12.9% of the game owns him as a £6.0m Crystal Palace defender; Chelsea have **agreed a ~£52m deal with personal terms settled and a medical booked**. Every one of those managers needs to move before the price/team changes. This is the highest-conviction actionable finding in this document.

2. **Trade the Trafford move, don't miss it.** Leeds have no goalkeepers left (Meslier to Arsenal, Darlow to Man Utd, Perri to Torino) and are "optimistic of signing this weekend." **James Trafford is priced £5.0m as Man City's third-choice** and becomes a promoted-but-established club's undisputed No.1. FFS's own price analysis already assumes the deal. A £5.0m starting keeper is a real budget lever.

3. **Harry Wilson's set-piece equity is not in the data.** FPL shows him with **no** penalty, corner or free-kick order. Reporting is explicit that he was Fulham's regular dead-ball taker and that his left foot fills a hole in Farke's right-footed setup. At £6.5m and 9.8% owned, he is the clearest example of the API being behind the news. Verify in the first friendly, then buy.

4. **Resolve the Liverpool penalty question before you commit £7.0m.** The FPL API says **Isak takes them**; Fantasy Football Scout and its pricing analysis say **Szoboszlai**. 40.9% of the game owns Szoboszlai on the latter assumption. One of these is wrong and it is worth roughly a penalty a month. Make it the first item of the pre-deadline sweep.

5. **De Zerbi's 3-4-3 makes Spurs' cheap defenders the structural value play of the window.** Six signings, five of them defensive or midfield, and a formation that fields **three centre-backs plus two wing-backs**. Senesi (£6.0m), Van Hecke (£5.0m), Van de Ven (£5.0m), Porro (£5.5m, Spurs' DFK #1) and **Robertson at £4.5m as a starting wing-back** are all live. Simultaneously, Spurs' *attack* is wrecked — Simons and Kulusevski out long-term, Odobert to November, Kudus flagged — so buy the back, not the front.

6. **Don't pay for Dúbravka's ownership; understand it.** 24.5% ownership on a **£4.0m** keeper who is **third or fourth choice** behind Kinský (14.8% at £4.5m) and Vicario. This is the game's bench-enabler consensus, not a minutes call. Confusing the two costs you a playing keeper.

7. **Kusi-Asare at 8.2% is the most over-owned unproven asset in the game.** A teenage Bayern reserve, £4.5m, described by FFS as a "youth option", at a club with a **brand-new manager**. The ownership is a price-point artefact. Fade it.

8. **The £117m and £116m signings both have a minutes caveat the fee hides.** **Rogers (34.8% owned)** is due a post-World Cup holiday and will **miss a large chunk of pre-season**; **Víctor Muñoz** likewise missed the start of Liverpool's tour. Rogers also gets **zero Chelsea set pieces** — Palmer is entrenched on penalties. Anderson at City is the cleaner minutes bet of the three, at £6.5m.

9. **Eight new managers means every 2025/26 minutes prior is suspect.** Liverpool (Iraola), Chelsea (Alonso), Man City (Maresca), Spurs (De Zerbi), Forest (Glasner), Palace (Sage), Fulham (Arbeloa), Bournemouth (Rose) — that is most of the top of the table. Weight pre-season friendly line-ups far above last season's usage for these eight, and hold a free transfer in reserve for GW2-GW3 corrections.

10. **The window is open until 1 September — after GW1 and GW2.** Man Utd will sign one of Koné or Baleba (capping Andrey Santos, thinning Brighton). Spurs are shopping for a striker and De Zerbi says business is "not finished". Palace must replace Lacroix. **Do not build a GW1 squad that cannot absorb a transfer, and do not treat the 25 July price list as final.**

---

### Appendix: reproducing the data pull

```
./.venv/Scripts/python.exe   # read db/raw/2026-07-25/bootstrap.json with encoding='utf-8'
# filter elements where team_join_date >= '2026-06-01'  -> 56 records
# dump penalties_order / corners_and_indirect_freekicks_order / direct_freekicks_order league-wide
# write output to file; do NOT print non-ASCII to a Windows cp1252 console
```

Note for the pipeline: `team_join_date` is `null` for a handful of players (Coppola/BHA, A.García/AVL, McNally/FUL, Pécsi/LIV, Burrowes/AVL). **A null join date correlates with a stale record** — Coppola has already been sold. Worth a validation rule in the snapshot loader.

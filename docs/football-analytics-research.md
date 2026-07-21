# The Best Reusable Football Analysis Tools & Repos on GitHub

*Deep research report — July 21, 2026. Six parallel research passes covering data access, analytics frameworks, computer vision, prediction modeling, visualization/FPL, and datasets/resources. Every repo below was verified against its live GitHub page (stars, license, last activity) — not search snippets. Star counts approximate.*

---

## TL;DR — The All-Star Stack

If you want the shortest path to a serious, reusable football analytics setup, these are the repos that matter most:

| Layer | Repo | Why |
|---|---|---|
| Data ingestion / interop | [PySport/kloppy](https://github.com/PySport/kloppy) (~530★, BSD-3) | Vendor-independent data model for event AND tracking data across 16+ providers. The backbone of the whole open ecosystem. v3.19.0, June 2026. |
| Free scraped data | [probberechts/soccerdata](https://github.com/probberechts/soccerdata) (~1.9k★, Apache-2.0) | One pandas API over FBref, Understat, WhoScored, Sofascore, SoFIFA, Club Elo, ESPN, Football-Data.co.uk. Active (v1.9.0, Apr 2026). |
| Free pro-grade data | [statsbomb/open-data](https://github.com/statsbomb/open-data) (~3.5k★) + [statsbombpy](https://github.com/statsbomb/statsbombpy) | Highest-quality free event + 360 data: Euro 2024, Copa América 2024, Women's Euro 2025, WC 2022, Messi's entire La Liga career. Non-commercial license. |
| Action valuation | [ML-KULeuven/socceraction](https://github.com/ML-KULeuven/socceraction) (~800★, MIT) | Canonical SPADL + VAEP + xT implementations. The academic gold standard. |
| Visualization | [andrewRowlinson/mplsoccer](https://github.com/andrewRowlinson/mplsoccer) (~530★, MIT) | THE football plotting library: 9 pitch coordinate systems, radars, pizza charts, heatmaps. Its star count badly understates its dominance. |
| Match prediction | [martineastwood/penaltyblog](https://github.com/martineastwood/penaltyblog) (~200★, MIT) | Dixon-Coles, bivariate Poisson, Bayesian models, Elo/Massey/Colley/Pi ratings, betting math — Cython-fast, very active (v1.11.0, June 2026). |
| Computer vision | [roboflow/sports](https://github.com/roboflow/sports) (~5.2k★, MIT) | Detection, tracking, team clustering, pitch homography from broadcast video. Updated July 2026. Lowest-friction CV entry point. |
| Tracking-data ML | [UnravelSports/unravelsports](https://github.com/UnravelSports/unravelsports) (~240★, MPL-2.0) | Tracking data → graph neural networks (PyTorch Geometric), Pressing Intensity, formation detection. The most impressive 2024–2026 entrant. |

---

## How the Ecosystem Fits Together

The open football analytics stack has consolidated into clear layers:

1. **Data layer** — StatsBomb open-data / Wyscout figshare / Metrica / SkillCorner / DFL IDSSE (free datasets), or scrapers (soccerdata, ScraperFC) for FBref/Understat/etc.
2. **Ingestion layer** — **kloppy** standardizes everything (coordinates, schemas) regardless of provider. Nearly every serious downstream tool consumes kloppy output.
3. **Analytics layer** — socceraction (SPADL/VAEP/xT), penaltyblog (match models), floodlight (physical metrics), unravelsports (GNNs), databallpy (event↔tracking sync).
4. **Presentation layer** — mplsoccer (Python), ggsoccer (R), d3-soccer (web).

Three orgs dominate: **PySport** (kloppy + ecosystem, non-profit), **KU Leuven DTAI** (socceraction, soccer_xg, un-xPass, soccerdata), and **SoccerNet** (Université de Liège; all things video/CV).

---

## 1. Data Access & Scraping

| Repo | Stars | License | Status | Notes |
|---|---|---|---|---|
| [probberechts/soccerdata](https://github.com/probberechts/soccerdata) | 1.9k | Apache-2.0 | ✅ Active | 8 sources, one DataFrame API, caching. Best overall. |
| [statsbomb/statsbombpy](https://github.com/statsbomb/statsbombpy) | 730 | Custom | ✅ Active (v1.21.0 Jul 2026) | Official client; works with free open data. Migrating to `hudl` org. |
| [oseymour/ScraperFC](https://github.com/oseymour/ScraperFC) | 400 | GPL-3.0 | ✅ Active (v4.5.0 Apr 2026) | Covers Capology salaries + Transfermarkt, which soccerdata lacks. |
| [dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) | 454 | CC0 | ✅ Weekly auto-refresh | 12 relational tables: 79k games, 37k players, 1.8M appearances. Also a model dbt+DVC+Actions pipeline. |
| [felipeall/transfermarkt-api](https://github.com/felipeall/transfermarkt-api) | 430 | MIT | ✅ Maintained | FastAPI REST service over Transfermarkt; free hosted instance; language-agnostic. |
| [amosbastian/understat](https://github.com/amosbastian/understat) | 184 | MIT | ✅ Fixed Dec 2025 | One of the few Understat clients updated after Understat's late-2025 API change. |
| [openfootball/football.json](https://github.com/openfootball/football.json) | 978 | CC0 | ✅ Active | Fixtures/results JSON through 2025-26. No player stats. |
| [martj42/international_results](https://github.com/martj42/international_results) | 509 | CC0 | ✅ Active | Every men's international since 1872 (~49k matches), clean CSVs. |
| [statsbomb/StatsBombR](https://github.com/statsbomb/StatsBombR) | 305 | Custom | ✅ Active | Now the best-maintained R data option. |
| [JaseZiv/worldfootballR](https://github.com/JaseZiv/worldfootballR) | 602 | GPL | ⚠️ **Archived Sep 2025** | Was the R standard. Read-only now; do not adopt for new work. |
| [federicorabanos/LanusStats](https://github.com/federicorabanos/LanusStats) | 131 | — | ✅ Active | One of the few maintained libs still covering FotMob + 365Scores. |
| [withqwerty/reep](https://github.com/withqwerty/reep) | 187 | CC0 | v0 frozen; v1 at reep.football | Canonical cross-provider ID mapping (Transfermarkt↔FBref↔Opta...). Solves a problem every multi-source project hits. |
| [American-Soccer-Analysis/itscalledsoccer](https://github.com/American-Soccer-Analysis/itscalledsoccer) | 60 | MIT | ✅ Active | xG/xPass/g+ for MLS, NWSL, USL. |

**Wrapper verdict:** for football-data.org and API-Football, no dominant open wrapper exists — call the REST APIs directly.

**Breakage intelligence (important):**
- **Understat** changed its API late 2025 — only libraries updated since (understat, soccerdata, ScraperFC, penaltyblog) work.
- **FotMob** tightened ToS ~2024 — dropped by worldfootballR and soccerdata.
- **FBref** rate-limits hard (≤1 req/3s; temp bans beyond) — soccerdata/ScraperFC build in throttling.
- **SoFIFA/Sofascore** sit behind Cloudflare — current tools use Playwright.

---

## 2. Analytics Frameworks, Metrics & Modeling

| Repo | Stars | License | Status | Notes |
|---|---|---|---|---|
| [PySport/kloppy](https://github.com/PySport/kloppy) | 532 | BSD-3 | ✅ Very active | The ingestion/standardization standard. 16+ providers, event + tracking. |
| [ML-KULeuven/socceraction](https://github.com/ML-KULeuven/socceraction) | 798 | MIT | 🔶 Maintenance mode (Aug 2024) | SPADL, VAEP, and the canonical xT implementation (`xthreat.py`). Stable, feature-frozen. |
| [ML-KULeuven/soccer_xg](https://github.com/ML-KULeuven/soccer_xg) | 253 | Apache-2.0 | 🔶 Low-frequency | Best open framework for *training* calibrated xG models (provider-agnostic). |
| [UnravelSports/unravelsports](https://github.com/UnravelSports/unravelsports) | 243 | MPL-2.0 | ✅ Active (v1.2.1 Jan 2026) | Tracking → Polars/graph datasets for GNNs; Pressing Intensity; formation detection (EFPI). |
| [floodlight-sports/floodlight](https://github.com/floodlight-sports/floodlight) | 126 | MIT | ✅ Active (v1.2.0 May 2026) | Sports-science angle: space control, metabolic power, entropy metrics. |
| [Alek050/databallpy](https://github.com/Alek050/databallpy) | 92 | MIT | ✅ Active | The only open library that *synchronizes* event and tracking data (Needleman-Wunsch). |
| [Friends-of-Tracking-Data-FoTD/LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking) | 353 | MIT | 💤 Dormant (2020) | The canonical open implementation of Spearman's pitch control + EPV. Reference code, not a package. |
| [ML-KULeuven/un-xPass](https://github.com/ML-KULeuven/un-xPass) | 59 | Apache-2.0 | 💤 Research-only | Pass creativity valuation with StatsBomb 360. Fork-to-learn. |
| [vivekjoshy/openskill.py](https://github.com/vivekjoshy/openskill.py) | 363 | MIT | ✅ Active | Fast open TrueSkill alternative; sport-agnostic rating engine. |
| [google-research/football](https://github.com/google-research/football) | 3.7k | Apache-2.0 | 💤 Dormant (2022) | RL environment, not analytics. Still the standard MARL soccer benchmark. |

---

## 3. Computer Vision & Tracking

| Repo | Stars | License | Status | Notes |
|---|---|---|---|---|
| [roboflow/sports](https://github.com/roboflow/sports) | 5.2k | MIT | ✅ Very active (Jul 2026) | Detection, ball tracking, team clustering, pitch keypoints + homography, open datasets. Best entry point. |
| [SoccerNet/sn-gamestate](https://github.com/SoccerNet/sn-gamestate) | 430 | GPL-3.0 | ✅ Active | Most complete pipeline: broadcast → calibrated minimap with tracked, team-assigned, jersey-identified players (CVPR'24, GS-HOTA metric). |
| [TrackingLaboratory/tracklab](https://github.com/TrackingLaboratory/tracklab) | 240 | MIT | ✅ Very active | The modular MOT framework under sn-gamestate: swappable detectors/re-ID/trackers, Hydra configs. MIT-licensed infrastructure. |
| [mguti97/PnLCalib](https://github.com/mguti97/PnLCalib) | 100 | GPL-2.0 | ✅ Active (Mar 2026) | SOTA camera calibration / pitch registration on all public benchmarks; pretrained model zoo. |
| [mkoshkina/jersey-number-pipeline](https://github.com/mkoshkina/jersey-number-pipeline) | 65 | CC BY-NC | 🔶 2024 | Reference jersey-number OCR pipeline (CVPRW 2024). Non-commercial license. |
| [SoccerNet/sn-reid](https://github.com/SoccerNet/sn-reid) | 85 | MIT | Challenge-cycle | Standard soccer re-ID dataset + TorchReID baselines. |
| [AtomScott/SportsLabKit](https://github.com/AtomScott/SportsLabKit) | 320 | GPL-3.0 | 💤 Stalled (2023) | Video→CSV tracking toolkit; successor datasets: SoccerTrack-v2, TeamTrack. |
| [abdullahtarek/football_analysis](https://github.com/abdullahtarek/football_analysis) | 980 | ❌ No license | 💤 2024 | Most popular YOLO tutorial project. Learn from it; don't build on it. |
| [tryolabs/soccer-video-analytics](https://github.com/tryolabs/soccer-video-analytics) | 300 | MIT | 💤 2023 | Polished possession/pass-count demo (Norfair tracker). Pedagogical. |
| [nreHieW/Eagle](https://github.com/nreHieW/Eagle) | 50 | ❌ No license | 🔶 Solo | Compact broadcast→tracking pipeline; blocked for reuse by missing license. |
| [lRomul/ball-action-spotting](https://github.com/lRomul/ball-action-spotting) | 135 | MIT | Frozen | 1st place SoccerNet 2023; the cleanest-engineered challenge solution to learn from. |
| [DonsetPG/narya](https://github.com/DonsetPG/narya) | 180 | MIT | ❌ Dead (TF1-era) | Historically important; superseded. |

**Reality check:** there is **no open-source TacticAI**. DeepMind never released the code — anything claiming otherwise is a third-party reimplementation. The open frontier stops at extracting tracking data; tactical models on top remain closed.

**License trap:** the two most impressive research stacks (sn-gamestate, jersey-number-pipeline) are GPL or non-commercial. The MIT safe harbors are roboflow/sports and tracklab.

---

## 4. Match Prediction & Statistical Modeling

| Repo | Stars | License | Status | Notes |
|---|---|---|---|---|
| [martineastwood/penaltyblog](https://github.com/martineastwood/penaltyblog) | 200 | MIT | ✅ Very active | Poisson/Dixon-Coles/bivariate/Bayesian models, Elo/Massey/Colley/Pi, betting math, scrapers. The one to install. |
| [georgedouzas/sports-betting](https://github.com/georgedouzas/sports-betting) | 750 | MIT | ✅ Very active (v0.14.0 Jul 2026) | sklearn-compatible betting framework: dataloaders (27 leagues, 1994–2026 + odds), leak-free backtesting, value bets, CLI/GUI/MCP server. |
| [LeoEgidi/footBayes](https://github.com/LeoEgidi/footBayes) | 57 | GPL-2 | ✅ Active (v2.1.0 2025) | The serious Bayesian option (R + Stan): double/bivariate Poisson, Skellam, dynamic models, CRAN. |
| [opisthokonta/goalmodel](https://github.com/opisthokonta/goalmodel) | 115 | GPL-3 | 🔶 Stable | Canonical frequentist R package: DC adjustment, Rue-Salvesen, time-weighting, scoring rules. |
| [anguswilliams91/bpl-next](https://github.com/anguswilliams91/bpl-next) | 5 | MIT | ✅ CI green | Numpyro Bayesian DC-family models. Massively under-starred; powers the Turing stack. |
| [alan-turing-institute/FootballTournamentPrediction](https://github.com/alan-turing-institute/FootballTournamentPrediction) | 72 | MIT | ✅ Active | Tournament Monte Carlo; beat FiveThirtyEight/Opta/Betfair in the 2022 WC contest; has 2026 WC forecasts. |
| [alan-turing-institute/AIrsenal](https://github.com/alan-turing-institute/AIrsenal) | 341 | MIT | ✅ Active (Jun 2026) | Full Bayesian ML pipeline that plays FPL autonomously. |
| [Torvaney/regista](https://github.com/Torvaney/regista) | 93 | GPL-3 | 💤 Stable | Elegant extensible Dixon-Coles in R (`dixoncoles_ext`). |
| [Torvaney/mezzala](https://github.com/Torvaney/mezzala) | 39 | Apache-2.0 | 💤 Static | Minimal Python DC with composable model blocks. |
| [lucasmaystre/kickscore](https://github.com/lucasmaystre/kickscore) | 62 | MIT | ✅ Revived 2025 | Gaussian-process dynamic ratings (KDD 2019); best research-grade time-varying rating library. |
| [Hicruben/world-cup-2026-prediction-model](https://github.com/Hicruben/world-cup-2026-prediction-model) | 82 | MIT | ✅ Active | Best of the 2026 WC wave: Elo + DC + Monte Carlo, honest backtests, published picks. |

**Caveat:** the `dixon-coles` GitHub topic is flooded with WC-2026 one-offs; nearly all will be abandoned post-tournament. FiveThirtyEight's SPI is frozen data only — no model code was ever released.

---

## 5. Visualization, Scouting Dashboards & FPL

| Repo | Stars | License | Status | Notes |
|---|---|---|---|---|
| [andrewRowlinson/mplsoccer](https://github.com/andrewRowlinson/mplsoccer) | 527 | MIT | ✅ Active | The Python standard. Also absorbed soccerplots' radars. |
| [znstrider/highlight_text](https://github.com/znstrider/highlight_text) | 133 | MIT | Stable | The styled-text micro-library behind virtually every polished football viz. |
| [Torvaney/ggsoccer](https://github.com/Torvaney/ggsoccer) | 204 | MIT | ✅ Active (CRAN) | The R standard: ggplot2 pitch layers, provider coordinate systems. |
| [probberechts/d3-soccer](https://github.com/probberechts/d3-soccer) | 75 | BSD-3 | ✅ v0.3.0 Dec 2024 | The only seriously maintained D3/web option; first-class SPADL support. |
| [griffisben/griffis_soccer_analysis](https://github.com/griffisben/griffis_soccer_analysis) | 133 | GPL-3.0 | ✅ Active | The most reusable open scouting-report generator (percentile radars, 70+ leagues of match reports via Streamlit). |
| [jakeyk11/football-data-analytics](https://github.com/jakeyk11/football-data-analytics) | 342 | Apache-2.0 | ✅ | Best applied end-to-end example: automated match reports, xG models, pass clustering. |
| [sonofacorner/soc-viz-of-the-week](https://github.com/sonofacorner/soc-viz-of-the-week) | 139 | ❌ No license | 💤 2023 | Production-quality matplotlib templates; license missing. |
| [eddwebster/football_analytics](https://github.com/eddwebster/football_analytics) | 2.7k | — | 🔶 | The largest single collection of notebooks + curated resources in the field. Cookbook, not a package. |

**FPL sub-ecosystem:**

| Repo | Stars | Status | Notes |
|---|---|---|---|
| [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) | 1.7k | ⚠️ Cadence cut | Canonical historical dataset (2016-17→2024-25); weekly updates stopped after 2024-25. |
| [olbauday/FPL-Core-Insights](https://github.com/olbauday/FPL-Core-Insights) | 167 | ✅ Active 2025/26 | The best *currently updated* FPL dataset (FPL API + match stats + Club Elo). |
| [solioanalytics/open-fpl-solver](https://github.com/solioanalytics/open-fpl-solver) | 176 | ✅ Active | The community-standard optimization toolkit (ex sertalpbilal/FPL-Optimization-Tools — renamed/moved). Apache-2.0, HiGHS solver. |
| [alan-turing-institute/AIrsenal](https://github.com/alan-turing-institute/AIrsenal) | 341 | ✅ Active | End-to-end: Bayesian modeling → optimization → automated team submission. |
| [amosbastian/fpl](https://github.com/amosbastian/fpl) | 328 | 🔶 Intermittent | The standard async FPL API wrapper. |
| [daniegr/OpenFPL](https://github.com/daniegr/OpenFPL) | 18 | ✅ New (2025) | Open fplreview-style projections (per-position ensembles, arXiv paper, pretrained). Pair with open-fpl-solver for a fully open stack. |

---

## 6. Open Datasets & Learning Resources

**Datasets (the fuel):**

| Dataset | What | License | Freshness |
|---|---|---|---|
| [statsbomb/open-data](https://github.com/statsbomb/open-data) (3.5k★) | Event + 360 data: Euro 2024, Copa América 2024, Women's Euro 2025, WC 2022/2018, Messi 2004–2021, women's leagues, CL finals to 1970/71 | Custom non-commercial | ✅ Actively extended |
| Wyscout/Pappalardo (figshare + [koenvo/wyscout-soccer-match-event-dataset](https://github.com/koenvo/wyscout-soccer-match-event-dataset)) | 1,941 matches: Big-5 leagues 2017/18 full seasons + WC18 + Euro16 | CC BY 4.0 | Frozen (2019) — still the best full-season corpus |
| [metrica-sports/sample-data](https://github.com/metrica-sports/sample-data) (486★) | 3 matches synced tracking + events | Informal | Frozen 2021; still the teaching standard |
| [SkillCorner/opendata](https://github.com/SkillCorner/opendata) (366★) | 10 matches broadcast tracking, A-League 2024/25 + physical data | MIT | ✅ Refreshed 2024/25 |
| [spoho-datascience/idsse-data](https://github.com/spoho-datascience/idsse-data) | **First official DFL release:** 7 Bundesliga matches, 25Hz TRACAB tracking + events (*Nature Sci Data* 2025) | CC BY 4.0 | ✅ New 2025 — low stars, huge value |
| PFF FC WC 2022 (via [kloppy PFF loader](https://kloppy.pysport.org/user-guide/loading-data/pff/)) | Broadcast tracking + events for all 64 WC 2022 matches | Free on request | Largest free tournament tracking release |
| [SoccerNet org](https://github.com/SoccerNet) | 500+ broadcast games: action spotting, tracking, calibration, re-ID, jersey, GSR, commentary (sn-echoes) | Mixed | ✅ Active challenge cycles through 2026 |

**Learning (the curriculum):**
- [soccermatics/Soccermatics](https://github.com/soccermatics/Soccermatics) — David Sumpter's live Uppsala course; the best structured free curriculum.
- [Friends-of-Tracking-Data-FoTD](https://github.com/Friends-of-Tracking-Data-FoTD) — SoccermaticsForPython (~420★), LaurieOnTracking (~353★, pitch control/EPV). Frozen but timeless.
- [devinpleuler/analytics-handbook](https://github.com/devinpleuler/analytics-handbook) (~1.7k★) — Toronto FC's analytics director's handbook, rebuilt on mplsoccer + kloppy.
- Awesome lists: [matiasmascioto/awesome-soccer-analytics](https://github.com/matiasmascioto/awesome-soccer-analytics) (~616★), [eddwebster/football_analytics](https://github.com/eddwebster/football_analytics) (~2.7k★), [diegopastor/awesome-football-analytics](https://github.com/diegopastor/awesome-football-analytics), [openfootball/awesome-football](https://github.com/openfootball/awesome-football) (has a live WC 2026 section).
- LLM frontier: [jyrao/MatchTime](https://github.com/jyrao/MatchTime) (EMNLP 2024, commentary generation), [SoccerNet/sn-echoes](https://github.com/SoccerNet/sn-echoes) (transcribed commentary).

---

## Cross-Domain Top 10 (Most "Cracked" + Most Reusable)

1. **kloppy** — the interoperability backbone; most actively maintained infrastructure in the space.
2. **statsbomb/open-data + statsbombpy** — the best free data in the sport, universally supported.
3. **roboflow/sports** — 5.2k★, MIT, updated this month; zero-to-working broadcast CV pipeline fastest.
4. **soccerdata** — the free-data workhorse; 8 sources, one API.
5. **mplsoccer** — the visualization standard everything renders through.
6. **socceraction** — SPADL/VAEP/xT; the shared vocabulary of event-data ML (feature-frozen but stable).
7. **penaltyblog** — the best match-modeling/ratings/betting toolkit, very active.
8. **transfermarkt-datasets** — CC0 living dataset + model data-engineering pipeline in one.
9. **sn-gamestate + tracklab + PnLCalib** — the academic CV stack: complete broadcast→minimap reconstruction.
10. **unravelsports** — the frontier: tracking data → GNNs, paper-backed, actively developed.

---

## Recommended Starter Stacks by Use Case

- **Event-data analysis (free):** statsbombpy → kloppy → socceraction (VAEP/xT) → mplsoccer. Learn via Soccermatics.
- **Multi-source scouting:** soccerdata + ScraperFC + transfermarkt-datasets → griffis_soccer_analysis-style percentile reports → mplsoccer radars. Use reep for ID mapping.
- **Match prediction/betting:** penaltyblog + sports-betting (backtesting) + soccerdata (data). Bayesian: footBayes (R) or bpl-next (Python).
- **Video → tracking data:** roboflow/sports to start; tracklab + PnLCalib for a serious pipeline; sn-gamestate as the full reference (mind the GPL).
- **Tracking-data research:** kloppy → unravelsports (GNNs) or databallpy (sync) or floodlight (physical); data from SkillCorner opendata, DFL idsse-data, PFF WC22, Metrica.
- **FPL:** FPL-Core-Insights (data) + OpenFPL (projections) + open-fpl-solver (optimization), or AIrsenal end-to-end.

---

## Landmines & Corrections (verified)

- **worldfootballR archived Sep 2025** — the R ecosystem's flagship is read-only; R users → StatsBombR or Python.
- **StatsBomb repos migrating to the `hudl` org** after the Hudl rebrand; old URLs redirect.
- **Understat's late-2025 API change** silently broke every unmaintained Understat scraper.
- **No open-source TacticAI** — the DeepMind/Liverpool corner-kick model was never released.
- **vaastav/Fantasy-Premier-League** no longer updates weekly (3×/season now).
- **`digitalghost-dev/premier-league`** (an oft-cited data-eng exemplar) now 404s.
- **soccerplots** is deprecated/merged into mplsoccer; the znstrider URL 404s.
- **License traps:** StatsBomb data is non-commercial; sn-gamestate is GPL-3.0; jersey-number-pipeline is CC BY-NC; popular tutorial repos (abdullahtarek/football_analysis, Eagle, soc-viz-of-the-week) have **no license at all**.
- **Wrapper graveyards:** football-data.org and API-Football have no healthy wrappers — use the REST APIs directly.

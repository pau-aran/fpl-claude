<div align="center">
  <h1>fpl-claude</h1>
  <p><b>The market prices reputation. We price expected points per million.</b></p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/season-2026%2F27-38003c?style=flat-square" alt="Season">
  <img src="https://img.shields.io/badge/backtest-%2B191%20over%2024%20GW-2ea043?style=flat-square" alt="Backtest">
  <img src="https://img.shields.io/badge/tests-68%20passing-2ea043?style=flat-square" alt="Tests">
</div>

## Why

Eleven million managers price Fantasy Premier League players on reputation, recency and hype.
A model can price them on minutes probability, fixture-adjusted underlying numbers and points
per million — and beat the crowd at it. That part is well understood.

The part nobody automates well is the other half of the job: the press conference three hours
before the deadline, the manager who rotates in Europe, the £64m release clause that will move
a striker in January. Pure solvers ignore it. Pure vibes ignore the maths.

fpl-claude is one season-long attempt to run both halves properly. **Claude is the manager.**
A Python pipeline turns every public data point into expected points and an optimal squad; the
manager overlays what the model cannot see, and writes down the reasoning — every gameweek, in
a memo you can audit a month later. Models propose. The manager disposes. The owner submits the
moves by hand.

## Scoreboard

Twenty-four gameweeks of the 2025/26 season, replayed point-in-time: every projection, news
sweep and decision made from data that existed before that deadline, with no leakage.

<table>
<tr>
  <td align="center" width="20%"><b>1380</b><br><sub>our points, GW1-24</sub></td>
  <td align="center" width="20%"><b>1189</b><br><sub>average manager</sub></td>
  <td align="center" width="20%"><b>+191</b><br><sub>edge, ~+8/GW</sub></td>
  <td align="center" width="20%"><b>1</b><br><sub>hit taken all season</sub></td>
  <td align="center" width="20%"><b>24/24</b><br><sub>captaincy adherence</sub></td>
</tr>
</table>

| Window | Ours | Avg | What it proved |
|---|---|---|---|
| **GW1-10** — the gate | 624 | 531 | The PLAN §4 backtest gate. Beat the field 7 weeks of 10; back half +68. Top-1% trajectory. |
| **GW11-16** — the grind | 317 | 279 | Five pipeline defects found and fixed by the weekly review loop, mid-run. |
| **GW17-24** — AFCON | 439 | 379 | The season's lowest-scoring stretch, ridden on banked free transfers. **Net +56, no chip played.** |

The interesting weeks are the ones we lost. GW2's bad hit is what built the hit-EV gate. GW23
refused a £14.0m Salah buy-back on written arithmetic and scored −6 for it — priced variance,
not process error, and the memo says so in advance. Every week's reasoning lives in
[`reports/backtest/2025-26/`](reports/backtest/2025-26/), including the ones that aged badly.

## How it works

```
      DATA                    MODELS                  DECISION              MANAGER
  ┌────────────┐         ┌──────────────┐        ┌──────────────┐      ┌─────────────┐
  │ FPL API    │         │ minutes      │        │ MILP (HiGHS) │      │ lock / ban  │
  │ Understat  │  ────▶  │ Dixon-Coles  │ ────▶  │ rules engine │ ──▶  │ captain     │
  │ odds CSVs  │         │ event rates  │        │ hit-EV gate  │      │ + WHY       │
  │ web + X    │         │ → xPts, 8 GW │        │ chip timing  │      └──────┬──────┘
  └────────────┘         └──────────────┘        └──────────────┘             │
   append-only            every value from        proposes a squad      decisions/gwNN.md
   point-in-time          config/rules/*.yaml     never an order        owner submits manually
```

Four rules hold the whole thing together:

1. **Value over reputation.** A £5.5m defender projected 4.2 beats a £7.5m name projected 4.6.
2. **Minutes are the market inefficiency.** Most FPL points are lost to benchings, not to bad picks.
3. **Process over outcome.** A −4 hit with +6 expected value that returned −2 was still right.
4. **Never miss a deadline.** A legal submission must always be derivable from cached data.

## Install

Python 3.11 or newer.

```bash
pip install -e ".[dev]"
pytest -q                                   # 68 tests
```

The model and optimizer layers are extras, installed with the phase that needs them:

```bash
pip install -e ".[models,optimize]"
pip install penaltyblog --no-deps           # its PyPI metadata pins a broken dep
```

`models/team.py` imports penaltyblog lazily and falls back to FDR-based expectations without it.

## Use

The pipeline runs from the CLI, but the intended interface is conversation. Ask in plain
language; the skills in `.claude/skills/` do the rest.

```
Refresh the data and tell me what changed since yesterday.
Who's the best £6m midfielder for the next four gameweeks?
Plan gameweek 12 — I have 2 free transfers and £0.4m in the bank.
Is Haaland worth captaining away at Anfield?
How did we actually do last week, and was it process or luck?
```

| Skill | Job | Cadence |
|---|---|---|
| `/fpl-refresh` | Snapshot the FPL API, rebuild DuckDB, report price moves and new flags | Daily |
| `/fpl-team-week-report` | Every PL team, every competition — results, injuries, congestion, rotation risk | Mondays |
| `/fpl-news-sweep` | Injuries, pressers, lineup leaks, X signal → structured risk table | Daily, always pre-deadline |
| `/fpl-scout` | Shortlists by xPts per £m, differentials, template drift, price radar | Weekly |
| `/fpl-fixture-planner` | 4-6 GW fixture runs; transfer paths planned ahead, not reacted to | Before any transfer |
| `/fpl-plan-gameweek` | The main pipeline → the decision memo in `decisions/` | T-48h, T-24h, T-2h |
| `/fpl-chip-strategy` | DGW/BGW detection, chip calendar upkeep | Weekly |
| `/fpl-review` | Predicted vs actual, luck vs process, calibration log, rank tracking | Post-GW |

Or run the layers directly:

```bash
python -m fpl_claude.data.fpl_api snapshot          # pull + snapshot current FPL state
python -m fpl_claude.models.projections --horizon 8 # ranked xPts table → db/projections/
python -m fpl_claude.backtest.run --data <vaastav-root> --gw 12 \
       --out reports/backtest/2025-26 --propose     # replay a GW: squad, transfer and chip proposal
```

## Design

**Everything a rule touches lives in YAML.** `config/rules/2026-27.yaml` holds budget, squad
shape, the 3-per-club cap, transfer banking, chip inventory and the full scoring map including
defensive contributions. FPL changes its rules every summer; every entry carries a
`verify_at_season_launch` flag, and a rule change is an edit to a config file, never to code.

**History is append-only.** `db/` keeps raw JSON snapshots alongside the DuckDB. We must always
be able to reconstruct what we knew *before* gameweek n — otherwise the backtests are fiction.

**Extract the commodity, build the edge.** The team model is a wrapped Dixon-Coles fit; the
minutes model is ours, because minutes are where the mispricing is. Third-party projection sites
are benchmarks to disagree with, never inputs.

**The manager layer is explicit, not implicit.** `--decision` takes locks, bans, captain
overrides and a written reason. Deviating from the optimizer is expected; deviating silently
is not. The GW17-24 window was won on refusals the solver wanted to make.

**The memo is the deliverable.** Transfers, XI, captain, chip, an EV table, the risks, and the
reasoning — dated, committed, and read back in the post-gameweek review to separate process from
variance. Not a spreadsheet you throw away on Sunday.

## Status

GW1 of 2026/27 is roughly three weeks out.

| Phase | State | Notes |
|---|---|---|
| **0 · Scaffold** | ✅ | Repo, API client, snapshotting, rules YAML, sources YAML, 8 skills |
| **1 · Data** | 🔶 | Pipelines written; the live pull needs a networked session — see `docs/environment.md` |
| **2 · Models** | ✅ | Minutes v1, Dixon-Coles, event rates, rules-driven xPts, price radar. **Gate passed** on the 24-GW replay |
| **3 · Optimizer** | ✅ | MILP squad/XI/captain/transfers/hits; chip mechanics + timing advisory shipped |
| **3b · Next** | ⬜ | Multi-period transfer path native to the MILP; live calibration loop off `db/projections/` |
| **4 · Skills live** | ⬜ | Full dry run on live 2026/27 data |
| **5 · Automation** | ⬜ | Scheduled sessions: Monday reports, daily sweeps, deadline runs, post-GW reviews |

Read [`STATE.md`](STATE.md) for the current handoff snapshot, [`PLAN.md`](PLAN.md) for the full
architecture, and [`NEXT-STEPS-IMPLEMENTATION.md`](NEXT-STEPS-IMPLEMENTATION.md) for the
buildable backlog.

## Map

```
CLAUDE.md                       the manager's persona and operating rules
PLAN.md                         full application plan — read before structural changes
STATE.md                        session handoff: where things stand right now
config/rules/2026-27.yaml       the FPL ruleset, verified at season launch
config/sources.yaml             curated news / strategy / X sources
src/fpl_claude/
  data/                         FPL API, football-data, prices, append-only snapshots
  models/                       minutes · team (Dixon-Coles) · rates · xPts · projections
  optimize/                     MILP squad optimizer, chip timing
  backtest/                     point-in-time season replay: store, simulator, CLI
  reports/                      weekly all-team report builder
  rules/                        YAML ruleset engine
decisions/gwNN.md               one memo per gameweek — the season's audit trail
reports/weekly/                 Monday reports on all 20 clubs
reports/backtest/2025-26/       the replay: memos, reviews, calibration, knowledge.md
db/                             DuckDB + raw snapshots, never overwritten
```

## Background

This started as a question about whether an agent could hold a full season of context — 38
deadlines, injuries that break plans two hours before kickoff, a chip calendar you commit to in
December and regret in February — and still make defensible decisions in week 30.

The 2025/26 replay says the maths is the easy part. What actually produced the edge was the
boring discipline: banking free transfers when nothing was worth buying, refusing the eleventh
churn transfer, writing down the expected value *before* the gameweek so the review could tell a
bad process from a bad bounce. The AFCON window was won by not playing a chip.

2026/27 is the live run. The first post-World Cup season, with late returners and early rotation
everywhere — which is exactly where a minutes model should earn its keep.

## Note

The owner submits every move manually. fpl-claude never connects to an FPL account and uses only
public, read-only data. It produces a memo; a human decides.

## License

MIT © 2026 Pau Aran

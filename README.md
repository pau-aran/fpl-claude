# fpl-claude

Moneyball for Fantasy Premier League: a Claude-managed FPL team for the 2026/27 season.

Claude is the manager. The pipeline gathers every FPL data point (players, prices,
fixtures, results, ownership), xG, team strength, odds signal, and news/injury
intelligence from curated web and X sources; models turn it into expected points; a
MILP optimizer proposes squads and transfers; Claude overlays qualitative judgment and
writes a reasoned decision memo per gameweek. The owner applies the moves manually —
no FPL account connection.

- **Plan:** [PLAN.md](PLAN.md)
- **Persona & operating rules:** [../CLAUDE.md](../CLAUDE.md)
- **Skills:** `../.claude/skills/fpl-*`
- **Weekly all-team reports:** `reports/weekly/`
- **Gameweek decision memos:** `decisions/`

## Quick start

```bash
cd fpl-claude
pip install -e .
python -m fpl_claude.data.fpl_api snapshot   # pull + snapshot current FPL state
python -m fpl_claude.reports.team_week       # build this week's team report skeletons
```

## Layout

- `config/rules/2026-27.yaml` — FPL ruleset (every rule flagged for verification at season launch)
- `config/sources.yaml` — curated FPL news/strategy/X sources used by news sweeps
- `src/fpl_claude/data/` — FPL API client + append-only snapshotting (DuckDB/JSON)
- `src/fpl_claude/models/` — minutes (built, v1) / team-strength (penaltyblog
  Dixon-Coles + FDR fallback) / rates + rules-driven xPts / projections CLI —
  see PLAN §4 for the build-vs-extract split and the pending backtest gate
- `src/fpl_claude/optimize/` — MILP squad optimizer (Phase 3)
- `src/fpl_claude/reports/` — weekly all-team report builder

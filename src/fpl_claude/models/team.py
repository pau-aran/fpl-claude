"""Team model — the layer we EXTRACT, not build.

Wraps penaltyblog's Dixon-Coles implementation (MIT, actively maintained — see
docs/football-analytics-research.md) fitted on football-data.co.uk results with
exponential time-decay weights. Output per fixture: expected goals for each side
and clean-sheet probabilities, read off the joint score grid.

When no historical results are available yet (fresh clone, pre-Phase-1 data), the
FDR fallback maps FPL fixture difficulty to league-average-anchored expected
goals so the projections pipeline always runs — it labels itself so downstream
output can say which source produced it (never silently).

penaltyblog import is lazy: the package's `socks` transitive dep is broken on
PyPI, so it installs via `--no-deps` (see pyproject comment); environments
without it still get the FDR fallback.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Standard Dixon-Coles time-decay: weight = exp(-xi * days_ago).
DEFAULT_XI = 0.0018

# FDR fallback: expected goals for a team vs an opponent of that difficulty,
# anchored to the PL average of ~1.43 goals per team per match.
LEAGUE_AVG_GOALS = 1.43
XG_BY_FDR = {1: 2.1, 2: 1.9, 3: 1.45, 4: 1.1, 5: 0.8}


@dataclass(frozen=True)
class FixtureExpectation:
    home_xg: float
    away_xg: float
    home_cs_prob: float  # P(away scores 0)
    away_cs_prob: float  # P(home scores 0)
    source: str  # "dixon_coles" | "fdr_fallback"


def _poisson_zero(lam: float) -> float:
    return math.exp(-lam)


def fdr_expectation(home_fdr: int, away_fdr: int) -> FixtureExpectation:
    """Fallback expectation from FPL difficulty ratings (each side's FDR is the
    difficulty of its opponent, so it maps directly to that side's attack)."""
    home_xg = XG_BY_FDR.get(home_fdr, LEAGUE_AVG_GOALS)
    away_xg = XG_BY_FDR.get(away_fdr, LEAGUE_AVG_GOALS)
    return FixtureExpectation(
        home_xg=round(home_xg, 3),
        away_xg=round(away_xg, 3),
        home_cs_prob=round(_poisson_zero(away_xg), 4),
        away_cs_prob=round(_poisson_zero(home_xg), 4),
        source="fdr_fallback",
    )


class TeamModel:
    """Dixon-Coles fitted on historical results (columns: date, home, away,
    home_goals, away_goals — FPL team names)."""

    def __init__(self, model, teams: set[str]):
        self._model = model
        self.teams = teams

    @classmethod
    def fit(cls, results: pd.DataFrame, xi: float = DEFAULT_XI) -> "TeamModel":
        from penaltyblog.models import DixonColesGoalModel

        results = results.dropna(subset=["home_goals", "away_goals"])
        days_ago = (results["date"].max() - results["date"]).dt.days.to_numpy(float)
        weights = np.exp(-xi * days_ago)
        model = DixonColesGoalModel(
            results["home_goals"].to_numpy(np.int64).copy(),
            results["away_goals"].to_numpy(np.int64).copy(),
            results["home"].to_numpy().copy(),
            results["away"].to_numpy().copy(),
            weights=weights.copy(),
        )
        model.fit()
        return cls(model, set(results["home"]) | set(results["away"]))

    def fixture(self, home: str, away: str) -> FixtureExpectation:
        pred = self._model.predict(home, away)
        grid = np.asarray(pred.grid)  # rows = home goals, cols = away goals
        home_goals = np.arange(grid.shape[0])
        away_goals = np.arange(grid.shape[1])
        return FixtureExpectation(
            home_xg=round(float(home_goals @ grid.sum(axis=1)), 3),
            away_xg=round(float(away_goals @ grid.sum(axis=0)), 3),
            home_cs_prob=round(float(grid.sum(axis=0)[0]), 4),
            away_cs_prob=round(float(grid.sum(axis=1)[0]), 4),
            source="dixon_coles",
        )

    def covers(self, *teams: str) -> bool:
        """Whether every named team appeared in the training data (promoted
        teams won't have — fall back to FDR for their fixtures)."""
        return all(t in self.teams for t in teams)

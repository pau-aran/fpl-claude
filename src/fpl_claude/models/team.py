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


# A team's Dixon-Coles rating is noise below this many matches in the training
# data: a promoted side that opened with one 3-0 win otherwise gets a rating
# that captains its defenders (2025/26 backtest, GW2). Below it -> FDR fallback.
MIN_TEAM_MATCHES = 5

# How far back a match still counts as evidence about a club's CURRENT side.
# A relegated club carries a full season of results that are stale by the time
# it returns; rating it on those is worse than admitting we don't know, because
# the squad, division and often the manager have all changed.
#
# 330 days, NOT a year-plus: an English season runs Aug-May, so any window
# wider than ~350 days reaches back through the summer break into the PREVIOUS
# season's tail. At 400 days Ipswich cleared this test on six matches played in
# April/May 2025 — the dying weeks of the relegation season that sent them
# down — which is precisely the evidence the check exists to reject.
RECENT_WINDOW_DAYS = 330

# Recent matches a club needs before its rating is trusted. Lower than
# MIN_TEAM_MATCHES: a promoted side that has played three PL games this season
# is thin, but it is thin evidence about the RIGHT team.
MIN_RECENT_MATCHES = 3


class TeamModel:
    """Dixon-Coles fitted on historical results (columns: date, home, away,
    home_goals, away_goals — FPL team names)."""

    def __init__(
        self,
        model,
        teams: set[str],
        match_counts: dict[str, int] | None = None,
        recent_counts: dict[str, int] | None = None,
    ):
        self._model = model
        self.teams = teams
        self.match_counts = match_counts or {t: MIN_TEAM_MATCHES for t in teams}
        # Absent recency data, treat the counts as recent — keeps hand-built
        # models (tests, callers with a bare match_counts) working as before.
        self.recent_counts = (
            recent_counts if recent_counts is not None else dict(self.match_counts)
        )

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
        counts = (
            pd.concat([results["home"], results["away"]]).value_counts().to_dict()
        )
        recent = results[
            results["date"] >= results["date"].max() - pd.Timedelta(days=RECENT_WINDOW_DAYS)
        ]
        recent_counts = (
            pd.concat([recent["home"], recent["away"]]).value_counts().to_dict()
        )
        return cls(model, set(counts), match_counts=counts, recent_counts=recent_counts)

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
        """Whether every named team has a USABLE rating.

        Two independent requirements, because a rating can fail in two ways:

          * ENOUGH matches (MIN_TEAM_MATCHES) — a promoted side that opened
            with one 3-0 win otherwise gets a rating that captains its
            defenders (2025/26 backtest, GW2);
          * RECENT matches (MIN_RECENT_MATCHES inside RECENT_WINDOW_DAYS) — a
            club can clear the count on a full season played two years ago and
            be modelled as if nothing had changed. Ipswich hit exactly this on
            the 2026/27 open: relegated in 2025, promoted again, and carrying
            38 stale matches. Only a name mismatch hid it.

        Teams failing either test use the FDR fallback instead.
        """
        return all(
            self.match_counts.get(t, 0) >= MIN_TEAM_MATCHES
            and self.recent_counts.get(t, 0) >= MIN_RECENT_MATCHES
            for t in teams
        )

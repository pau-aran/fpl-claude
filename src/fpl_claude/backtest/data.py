"""Point-in-time reconstruction of a past season from vaastav CSV archives.

The whole value of the backtest gate (PLAN §4) is that it is honest: at GW n we
may only know what a manager knew before the GW n deadline. This module rebuilds
that state from the vaastav/Fantasy-Premier-League archive:

  bootstrap_at(n)   synthetic FPL bootstrap: cumulative stats through GW n-1
                    ONLY, prices as of GW n, zeroed season stats at GW 1
  fixtures_at(n)    fixture list where GWs < n are finished and >= n are not
  prior_bootstrap() the previous season's final players_raw, remapped to this
                    season's player ids via the cross-season `code` key
  results_through(n) match results (prior season + GWs < n) for Dixon-Coles
  actuals(n)        what actually happened in GW n — used ONLY for scoring,
                    never fed to models

Known fidelity gaps (documented, revisited by the weekly review loop):
  - No historical injury/availability flags: `status` is always "a", so the
    minutes model sees benchings only through the starts record. Real deadline
    decisions had press-conference news we cannot replay.
  - Fixture list is the season's FINAL schedule; a fixture postponed mid-season
    appears at its rescheduled GW from the start.
  - `selected_by_percent` is the raw `selected` count scaled by a nominal
    player base — fine for ranking, not for exact EO.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

POSITION_TO_ELEMENT_TYPE = {"GK": 1, "GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}

# Cumulative merged_gw stat -> bootstrap element field.
STAT_FIELDS = {
    "minutes": "minutes",
    "starts": "starts",
    "expected_goals": "expected_goals",
    "expected_assists": "expected_assists",
    "saves": "saves",
    "defensive_contribution": "defensive_contribution",
    "bonus": "bonus",
    "goals_scored": "goals_scored",
    "assists": "assists",
    "total_points": "total_points",
}

NOMINAL_MANAGER_BASE = 11_000_000  # scales `selected` counts to a rough EO%


class SeasonStore:
    """Read-only view over one season's vaastav data (plus the prior season)."""

    def __init__(self, root: Path, season: str = "2025-26", prior: str = "2024-25"):
        self.root = Path(root)
        self.season = season
        self.prior = prior
        d = self.root / season
        self.merged = pd.read_csv(d / "merged_gw.csv")
        self.players = pd.read_csv(d / "players_raw.csv")
        self.fixtures = pd.read_csv(d / "fixtures.csv")
        self.teams = pd.read_csv(d / "teams.csv")
        pd_dir = self.root / prior
        self.prior_players = pd.read_csv(pd_dir / "players_raw.csv")
        self.prior_fixtures = pd.read_csv(pd_dir / "fixtures.csv")
        self.prior_teams = pd.read_csv(pd_dir / "teams.csv")

    # ------------------------------------------------------------------ bootstrap

    @lru_cache(maxsize=64)
    def bootstrap_at(self, gw: int) -> dict:
        """Synthetic bootstrap as known before the GW `gw` deadline."""
        past = self.merged[self.merged["GW"] < gw]
        sums = past.groupby("element")[list(STAT_FIELDS)].sum() if len(past) else None

        prices = self._prices_at(gw)
        selected = self._selected_at(gw)
        team_at = self._teams_at(gw)
        position_at = self._positions_at(gw)

        elements = []
        for p in self.players.itertuples():
            pid = int(p.id)
            row = sums.loc[pid] if sums is not None and pid in sums.index else None
            stats = {
                field: (float(row[stat]) if row is not None else 0)
                for stat, field in STAT_FIELDS.items()
            }
            stats["minutes"] = int(stats["minutes"])
            stats["starts"] = int(stats["starts"])
            element_type = position_at.get(pid, int(p.element_type))
            if element_type not in (1, 2, 3, 4):
                continue  # e.g. assistant-manager pseudo-players
            elements.append(
                {
                    "id": pid,
                    "code": int(p.code),
                    "web_name": p.web_name,
                    # players_raw carries END-of-season team/position: using it
                    # would leak January transfers into August. merged_gw rows
                    # at-or-before this GW are the point-in-time truth.
                    "team": team_at.get(pid, int(p.team)),
                    "element_type": element_type,
                    "now_cost": prices.get(pid, int(p.now_cost)),
                    "selected_by_percent": selected.get(pid, "0.0"),
                    "status": "a",  # no historical flags in the archive
                    "chance_of_playing_next_round": None,
                    **stats,
                }
            )

        events = [
            {
                "id": int(e),
                "finished": int(e) < gw,
                # Deadlines are synthetic: models only ask "is this GW still
                # ahead of us", so past GWs sit in the past and future ones
                # are spaced a week apart from now.
                "deadline_time": _synthetic_deadline(int(e), gw),
            }
            for e in sorted(self.merged["GW"].unique())
        ]

        return {
            "elements": elements,
            "teams": self.teams.to_dict("records"),
            "events": events,
        }

    def _prices_at(self, gw: int) -> dict[int, int]:
        """Player price (API tenths) as of GW `gw`: that GW's value, else the
        last value seen before it, else the first value ever seen."""
        m = self.merged
        known = m[m["GW"] <= gw].sort_values("GW").groupby("element")["value"].last()
        future = m[m["GW"] > gw].sort_values("GW").groupby("element")["value"].first()
        prices = future.to_dict()
        prices.update(known.to_dict())  # anything seen by `gw` wins
        return {int(k): int(v) for k, v in prices.items()}

    def _point_in_time_column(self, gw: int, column: str) -> dict[int, str]:
        """Per-player value of `column` as known at GW `gw`: latest row at or
        before the GW, else the earliest later row (players registered later)."""
        m = self.merged
        past = m[m["GW"] <= gw].sort_values("GW").groupby("element")[column].last()
        future = m[m["GW"] > gw].sort_values("GW").groupby("element")[column].first()
        values = future.to_dict()
        values.update(past.to_dict())
        return {int(k): v for k, v in values.items()}

    @lru_cache(maxsize=64)
    def _teams_at(self, gw: int) -> dict[int, int]:
        name_to_id = {t.name: int(t.id) for t in self.teams.itertuples()}
        return {
            pid: name_to_id[name]
            for pid, name in self._point_in_time_column(gw, "team").items()
            if name in name_to_id
        }

    @lru_cache(maxsize=64)
    def _positions_at(self, gw: int) -> dict[int, int]:
        return {
            pid: POSITION_TO_ELEMENT_TYPE[pos]
            for pid, pos in self._point_in_time_column(gw, "position").items()
            if pos in POSITION_TO_ELEMENT_TYPE
        }

    def _selected_at(self, gw: int) -> dict[int, str]:
        m = self.merged[self.merged["GW"] == gw]
        if m.empty:
            return {}
        sel = m.groupby("element")["selected"].first()
        return {
            int(k): f"{100.0 * float(v) / NOMINAL_MANAGER_BASE:.1f}"
            for k, v in sel.items()
        }

    # ------------------------------------------------------------------ fixtures

    def fixtures_at(self, gw: int) -> list[dict]:
        """Fixture dicts as of GW `gw` (finished flag reflects GWs played)."""
        out = []
        for f in self.fixtures.itertuples():
            if pd.isna(f.event):
                continue
            event = int(f.event)
            out.append(
                {
                    "id": int(f.id),
                    "event": event,
                    "team_h": int(f.team_h),
                    "team_a": int(f.team_a),
                    "team_h_difficulty": int(f.team_h_difficulty),
                    "team_a_difficulty": int(f.team_a_difficulty),
                    "kickoff_time": f.kickoff_time,
                    "finished": event < gw,
                }
            )
        return out

    # ------------------------------------------------------------------ priors

    @lru_cache(maxsize=1)
    def prior_bootstrap(self) -> dict:
        """Prior season's final stats, remapped to THIS season's player ids.

        FPL ids reset every season; `code` is the stable cross-season key. New
        signings and promoted-team players have no prior row — the minutes and
        rates layers treat them as genuine unknowns, which is honest.
        """
        code_to_id = {int(p.code): int(p.id) for p in self.players.itertuples()}
        elements = []
        for p in self.prior_players.to_dict("records"):
            pid = code_to_id.get(int(p["code"]))
            if pid is None:
                continue
            elements.append(
                {
                    "id": pid,
                    "web_name": p["web_name"],
                    "element_type": int(p["element_type"]),
                    "minutes": int(p.get("minutes") or 0),
                    "starts": int(p.get("starts") or 0),
                    "expected_goals": p.get("expected_goals", 0),
                    "expected_assists": p.get("expected_assists", 0),
                    "saves": p.get("saves", 0),
                    "defensive_contribution": p.get("defensive_contribution", 0) or 0,
                    "bonus": p.get("bonus", 0),
                }
            )
        return {"elements": elements}

    # ------------------------------------------------------------------ results

    def results_through(self, gw: int) -> pd.DataFrame:
        """Finished-match results for the team model: the whole prior season
        plus this season's GWs before `gw`. Columns: date, home, away,
        home_goals, away_goals (FPL team names)."""
        frames = [
            _results_frame(self.prior_fixtures, self.prior_teams),
            _results_frame(
                self.fixtures[self.fixtures["event"] < gw], self.teams
            ),
        ]
        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------ actuals

    def actuals(self, gw: int) -> pd.DataFrame:
        """What GW `gw` actually produced, per player: points and minutes
        (summed over double-gameweek fixtures). Scoring only — never model input."""
        m = self.merged[self.merged["GW"] == gw]
        out = (
            m.groupby("element")
            .agg(points=("total_points", "sum"), minutes=("minutes", "sum"))
            .reset_index()
            .rename(columns={"element": "id"})
        )
        return out


def _results_frame(fixtures: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    names = teams.set_index("id")["name"]
    done = fixtures[fixtures["finished"] == True]  # noqa: E712 — pandas mask
    return pd.DataFrame(
        {
            "date": pd.to_datetime(done["kickoff_time"], utc=True).dt.tz_localize(None),
            "home": done["team_h"].map(names),
            "away": done["team_a"].map(names),
            "home_goals": done["team_h_score"],
            "away_goals": done["team_a_score"],
        }
    )


def _synthetic_deadline(event: int, current_gw: int) -> str:
    """ISO deadline placing past GWs behind us and GW `current_gw` onward ahead."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    delta = timedelta(days=7 * (event - current_gw) + 1)
    return (now + delta).strftime("%Y-%m-%dT%H:%M:%SZ")

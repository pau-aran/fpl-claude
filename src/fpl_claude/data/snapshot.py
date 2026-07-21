"""Load raw FPL snapshots into DuckDB for querying.

Tables (rebuilt from db/raw/ on demand — raw JSON is the source of truth):
  players(snapshot_date, id, web_name, team_id, position, now_cost, status, news,
          chance_next_round, selected_by_percent, form, total_points, minutes, ...)
  teams(snapshot_date, id, name, short_name, strength_overall_home/away, ...)
  fixtures(snapshot_date, id, event, kickoff_time, team_h, team_a, team_h_score,
           team_a_score, finished, team_h_difficulty, team_a_difficulty)

Price history and flag history fall out of querying `players` across snapshot_dates.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from .fpl_api import PROJECT_ROOT, RAW_DIR

DB_PATH = PROJECT_ROOT / "db" / "fpl.duckdb"

POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

PLAYER_COLUMNS = [
    "id", "web_name", "first_name", "second_name", "team", "element_type", "now_cost",
    "status", "news", "news_added", "chance_of_playing_next_round",
    "selected_by_percent", "form", "total_points", "minutes", "goals_scored",
    "assists", "clean_sheets", "bonus", "bps", "transfers_in_event",
    "transfers_out_event", "cost_change_event",
]


def _iter_snapshot_days(raw_dir: Path = RAW_DIR):
    if not raw_dir.exists():
        return
    for day_dir in sorted(raw_dir.iterdir()):
        if day_dir.is_dir() and (day_dir / "bootstrap.json").exists():
            yield day_dir


def load_frames(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Flatten all raw snapshots into players/teams/fixtures DataFrames."""
    players, teams, fixtures = [], [], []
    for day_dir in _iter_snapshot_days(raw_dir):
        day = day_dir.name
        bootstrap = json.loads((day_dir / "bootstrap.json").read_text())

        p = pd.DataFrame(bootstrap["elements"])
        p = p[[c for c in PLAYER_COLUMNS if c in p.columns]].copy()
        p.insert(0, "snapshot_date", day)
        p["position"] = p["element_type"].map(POSITION_BY_ELEMENT_TYPE)
        players.append(p)

        t = pd.DataFrame(bootstrap["teams"])
        t.insert(0, "snapshot_date", day)
        teams.append(t)

        fixtures_file = day_dir / "fixtures.json"
        if fixtures_file.exists():
            f = pd.DataFrame(json.loads(fixtures_file.read_text()))
            if not f.empty:
                f = f.drop(columns=["stats"], errors="ignore")
                f.insert(0, "snapshot_date", day)
                fixtures.append(f)

    return {
        "players": pd.concat(players, ignore_index=True) if players else pd.DataFrame(),
        "teams": pd.concat(teams, ignore_index=True) if teams else pd.DataFrame(),
        "fixtures": pd.concat(fixtures, ignore_index=True) if fixtures else pd.DataFrame(),
    }


def rebuild_db(db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> Path:
    """(Re)build the DuckDB database from raw snapshots."""
    frames = load_frames(raw_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for name, frame in frames.items():
            con.execute(f"DROP TABLE IF EXISTS {name}")
            if frame.empty:
                continue
            con.register("frame_view", frame)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM frame_view")
            con.unregister("frame_view")
    finally:
        con.close()
    return db_path


if __name__ == "__main__":
    print(f"rebuilt: {rebuild_db()}")

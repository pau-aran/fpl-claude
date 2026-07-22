"""football-data.co.uk results/odds CSVs — training data for the team model.

Season files live at https://www.football-data.co.uk/mmz4281/{code}/E0.csv where
code is e.g. "2526" for 2025/26. Downloads are append-only under
db/raw/football-data/ (a season already on disk is never re-fetched once final;
the current season is refreshed on each fetch).

CLI:  python -m fpl_claude.data.football_data fetch 2425 2526
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

from .fpl_api import RAW_DIR, USER_AGENT

FOOTBALL_DATA_DIR = RAW_DIR / "football-data"
URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"

# football-data.co.uk team names -> FPL bootstrap `name` values.
# Names not listed pass through unchanged (most already match).
TO_FPL_NAME = {
    "Man United": "Man Utd",
    "Tottenham": "Spurs",
    "Nott'm Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield Utd",
}


def fetch(season_codes: list[str], out_dir: Path = FOOTBALL_DATA_DIR) -> list[Path]:
    """Download season CSVs; only the newest (current) season is re-fetched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    newest = max(season_codes)
    paths = []
    for code in season_codes:
        path = out_dir / f"E0-{code}.csv"
        if path.exists() and code != newest:
            paths.append(path)
            continue
        resp = requests.get(
            URL_TEMPLATE.format(code=code),
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        path.write_bytes(resp.content)
        paths.append(path)
    return paths


def load_results(paths: list[Path] | None = None) -> pd.DataFrame:
    """All downloaded results as (date, home, away, home_goals, away_goals),
    team names normalized to FPL bootstrap names."""
    if paths is None:
        paths = sorted(FOOTBALL_DATA_DIR.glob("E0-*.csv"))
    if not paths:
        return pd.DataFrame(columns=["date", "home", "away", "home_goals", "away_goals"])
    frames = []
    for path in paths:
        raw = pd.read_csv(path)
        raw = raw.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        frames.append(
            pd.DataFrame(
                {
                    "date": pd.to_datetime(raw["Date"], dayfirst=True),
                    "home": raw["HomeTeam"].replace(TO_FPL_NAME),
                    "away": raw["AwayTeam"].replace(TO_FPL_NAME),
                    "home_goals": raw["FTHG"].astype(int),
                    "away_goals": raw["FTAG"].astype(int),
                }
            )
        )
    return pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "fetch":
        for path in fetch(sys.argv[2:]):
            print(f"fetched: {path}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

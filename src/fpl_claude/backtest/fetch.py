"""Fetch the vaastav/Fantasy-Premier-League archive files a season replay needs.

GitHub raw is reachable from the cloud sandbox even while the FPL API is not
(docs/environment.md), so backtests can always self-provision. Files land under
<dest>/<season>/ matching what backtest.data.SeasonStore expects.

CLI: python -m fpl_claude.backtest.fetch --dest DIR [--season 2025-26] [--prior 2024-25]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

BASE = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

SEASON_FILES = ["players_raw.csv", "fixtures.csv", "teams.csv", "gws/merged_gw.csv"]
PRIOR_FILES = ["players_raw.csv", "fixtures.csv", "teams.csv"]


def fetch_season(dest: Path, season: str, files: list[str]) -> None:
    for name in files:
        out = dest / season / Path(name).name
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            print(f"kept    {out}")
            continue
        url = f"{BASE}/{season}/{name}"
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        out.write_bytes(resp.content)
        print(f"fetched {out} ({len(resp.content):,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--prior", default="2024-25")
    args = parser.parse_args()

    dest = Path(args.dest)
    fetch_season(dest, args.season, SEASON_FILES)
    fetch_season(dest, args.prior, PRIOR_FILES)


if __name__ == "__main__":
    main()

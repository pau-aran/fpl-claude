"""Provision a live-season snapshot when the FPL API is egress-blocked.

`fpl_claude.data.fpl_api.snapshot()` is the source of truth and stays so. This
script is the FALLBACK for a sandbox whose egress policy denies
`fantasy.premierleague.com` (the cloud session returns 403 to CONNECT while
`raw.githubusercontent.com` is allowed) — it rebuilds the same two payloads,
`bootstrap.json` and `fixtures.json`, out of the vaastav
`Fantasy-Premier-League` mirror of the same API, plus the football-data-shaped
results the Dixon-Coles team model trains on.

Three things it must get right, because each one silently corrupts a squad build:

1. **The mirror's `players_raw.csv` for a NOT-YET-STARTED season carries the
   PREVIOUS season's accumulated stats against CURRENT-season ids.** Verified on
   the 2026/27 file: 452 of 457 matched rows are byte-identical to the 2025/26
   file, and Isak reads 694 minutes / 8 starts — his Liverpool half-season, not
   a 2026/27 total. The live pre-season bootstrap has all of those at zero. So
   every accumulated stat column is ZEROED here, and the prior is supplied
   separately through `--prior-season-csv` exactly as the live pipeline does it.
2. **A zero-filled prior row is not a missing prior row.** The mirror gives every
   2026/27 player a row; 110 of them are new and carry zeros. Feeding those as
   priors is defect D3 ("a present row of zeros walks straight through the same
   door") — a zeroed prior reads as "played and produced nothing". Hence the
   prior must come from the real completed-season file, which simply omits them.
3. **Results for the team model** come from the mirror's `fixtures.csv` for
   completed seasons (they carry `team_h_score`/`team_a_score`), written out in
   football-data.co.uk's E0 column shape so `football_data.load_results()` reads
   them unchanged — including `Date` as dd/mm/YYYY, which that loader parses
   `dayfirst=True`.

Identity, prices, ownership, flags, news, set-piece orders and `ep_next` are all
carried through untouched: they are current-season fields and are what the
squad build actually reads.

CLI:  python notebooks/provision_from_vaastav.py [--season 2026-27]
          [--prior-season 2025-26] [--results-seasons 2024-25,2025-26]
          [--out-date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from fpl_claude.data.fpl_api import PROJECT_ROOT, RAW_DIR, USER_AGENT

MIRROR = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
FOOTBALL_DATA_DIR = RAW_DIR / "football-data"
VAASTAV_DIR = PROJECT_ROOT / "db" / "vaastav"

# FPL publishes the deadline 90 minutes before a gameweek's first kick-off.
DEADLINE_LEAD = timedelta(minutes=90)

# Everything a player ACCUMULATES by playing. The live pre-season bootstrap has
# each of these at zero; the mirror carries last season's value. Anything not
# listed here is identity, price, ownership, availability or set-piece duty —
# current-season truth that must survive untouched.
ACCUMULATED_INT = (
    "assists", "bonus", "bps", "clean_sheets", "clearances_blocks_interceptions",
    "defensive_contribution", "dreamteam_count", "event_points", "goals_conceded",
    "goals_scored", "minutes", "own_goals", "penalties_missed", "penalties_saved",
    "recoveries", "red_cards", "saves", "starts", "tackles", "total_points",
    "transfers_in", "transfers_in_event", "transfers_out", "transfers_out_event",
    "yellow_cards",
)
ACCUMULATED_FLOAT = (
    "clean_sheets_per_90", "creativity", "defensive_contribution_per_90",
    "expected_assists", "expected_assists_per_90", "expected_goal_involvements",
    "expected_goal_involvements_per_90", "expected_goals", "expected_goals_conceded",
    "expected_goals_conceded_per_90", "expected_goals_per_90", "form",
    "goals_conceded_per_90", "ict_index", "influence", "points_per_game",
    "saves_per_90", "starts_per_90", "threat", "value_form", "value_season",
)


def _fetch(season: str, name: str, cache: Path) -> Path:
    """Download `data/{season}/{name}.csv` from the mirror once, then reuse it."""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{name}.csv"
    if path.exists():
        return path
    resp = requests.get(
        f"{MIRROR}/{season}/{name}.csv", headers={"User-Agent": USER_AGENT}, timeout=60
    )
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return path


def _cell(value):
    """CSV -> JSON: NaN becomes None, numpy scalars become Python scalars."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def build_bootstrap(season: str, cache: Path) -> dict:
    players = pd.read_csv(_fetch(season, "players_raw", cache))
    teams = pd.read_csv(_fetch(season, "teams", cache))
    fixtures = pd.read_csv(_fetch(season, "fixtures", cache))

    for col in ACCUMULATED_INT:
        if col in players.columns:
            players[col] = 0
    for col in ACCUMULATED_FLOAT:
        if col in players.columns:
            players[col] = 0.0

    elements = [
        {k: _cell(v) for k, v in row.items()} for row in players.to_dict("records")
    ]
    team_rows = [{k: _cell(v) for k, v in row.items()} for row in teams.to_dict("records")]

    kickoffs = fixtures.dropna(subset=["event"]).copy()
    kickoffs["event"] = kickoffs["event"].astype(int)
    kickoffs["kickoff"] = pd.to_datetime(kickoffs["kickoff_time"], utc=True)
    events = []
    for gw, grp in kickoffs.groupby("event"):
        deadline = grp["kickoff"].min() - DEADLINE_LEAD
        events.append(
            {
                "id": int(gw),
                "name": f"Gameweek {int(gw)}",
                "deadline_time": deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "finished": bool(grp["finished"].all()),
                "is_current": False,
                "is_next": False,
                "is_previous": False,
            }
        )
    events.sort(key=lambda e: e["id"])
    for event in events:  # the next unfinished GW is the one the deadline belongs to
        if not event["finished"]:
            event["is_next"] = True
            break

    return {"elements": elements, "teams": team_rows, "events": events}


def build_fixtures(season: str, cache: Path) -> list[dict]:
    fixtures = pd.read_csv(_fetch(season, "fixtures", cache))
    fixtures = fixtures.drop(columns=[c for c in ("stats",) if c in fixtures.columns])
    out = []
    for row in fixtures.to_dict("records"):
        fx = {k: _cell(v) for k, v in row.items()}
        if fx.get("event") is not None:
            fx["event"] = int(fx["event"])
        out.append(fx)
    return out


def write_results(seasons: list[str], cache_root: Path) -> Path:
    """Completed-season fixtures -> football-data E0 CSVs for the team model.

    The cache is per SEASON, not shared: every season's file is named
    `fixtures.csv`, so a single shared directory silently serves season one's
    results for season two. That is not a cosmetic bug — it hands the team model
    two copies of the same season, and a club relegated the year before then
    clears the recency guard on results the guard exists to reject.
    """
    FOOTBALL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for season in seasons:
        cache = cache_root / season
        fixtures = pd.read_csv(_fetch(season, "fixtures", cache))
        teams = pd.read_csv(_fetch(season, "teams", cache)).set_index("id")["name"].to_dict()
        played = fixtures.dropna(subset=["team_h_score", "team_a_score"]).copy()
        frame = pd.DataFrame(
            {
                "Date": pd.to_datetime(played["kickoff_time"], utc=True).dt.strftime(
                    "%d/%m/%Y"
                ),
                "HomeTeam": played["team_h"].map(teams),
                "AwayTeam": played["team_a"].map(teams),
                "FTHG": played["team_h_score"].astype(int),
                "FTAG": played["team_a_score"].astype(int),
            }
        )
        if frame[["HomeTeam", "AwayTeam"]].isna().any().any():
            raise ValueError(f"{season}: fixture rows reference unknown team ids")
        code = season[2:4] + season[5:7]  # 2025-26 -> 2526, football-data's own key
        path = FOOTBALL_DATA_DIR / f"E0-{code}.csv"
        frame.to_csv(path, index=False)
        written.append((path, len(frame)))
    for path, n in written:
        print(f"results written: {path} ({n} matches)")
    return FOOTBALL_DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2026-27")
    parser.add_argument("--prior-season", default="2025-26")
    parser.add_argument("--results-seasons", default="2024-25,2025-26")
    parser.add_argument("--out-date", default=None, help="snapshot dir name (default: today)")
    args = parser.parse_args()

    cache_root = PROJECT_ROOT / "db" / "vaastav"
    bootstrap = build_bootstrap(args.season, cache_root / args.season)
    fixtures = build_fixtures(args.season, cache_root / args.season)

    day = args.out_date or datetime.now(UTC).date().isoformat()
    day_dir = RAW_DIR / day
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "bootstrap.json").write_text(
        json.dumps(bootstrap, separators=(",", ":")), encoding="utf-8"
    )
    (day_dir / "fixtures.json").write_text(
        json.dumps(fixtures, separators=(",", ":")), encoding="utf-8"
    )
    news_dates = [
        str(e.get("news_added"))[:10] for e in bootstrap["elements"] if e.get("news_added")
    ]
    (day_dir / "meta.json").write_text(
        json.dumps(
            {
                "fetched_at_utc": datetime.now(UTC).isoformat(),
                "source": f"{MIRROR}/{args.season} (FPL API mirror)",
                "reason": "fantasy.premierleague.com is egress-blocked in this sandbox",
                "content_as_of_news_added_max": max(news_dates) if news_dates else None,
                "accumulated_stats_zeroed": True,
                "prior_season_for_stats": args.prior_season,
            }
        ),
        encoding="utf-8",
    )
    print(f"snapshot written: {day_dir}")
    print(
        f"  {len(bootstrap['elements'])} players, {len(bootstrap['teams'])} teams, "
        f"{len(fixtures)} fixtures, {len(bootstrap['events'])} events"
    )
    print(f"  latest team news in payload: {max(news_dates) if news_dates else 'none'}")

    prior_path = _fetch(
        args.prior_season, "players_raw", cache_root / args.prior_season
    )
    print(f"prior season csv: {prior_path}")
    write_results([s for s in args.results_seasons.split(",") if s], cache_root)


if __name__ == "__main__":
    main()

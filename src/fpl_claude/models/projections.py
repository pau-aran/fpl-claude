"""Projections pipeline: minutes x rates x team model -> xPts per GW -> ranked table.

Glues the model layers together over the planning horizon from
config/rules (policies.planning_horizon_gws, policies.horizon_decay):

  1. bootstrap + fixtures (live, or --from-snapshot for point-in-time runs)
  2. minutes model v1 (+ optional priors from --prior-snapshot, + overlays)
  3. per-90 rates blended with the same prior snapshot
  4. team model: Dixon-Coles if football-data results are on disk and
     penaltyblog is importable, FDR fallback otherwise (labeled per player)
  5. rules-driven scoring map -> per-GW xPts, decayed horizon total, xPts/£m

Output: DataFrame + CSV under db/projections/ (audit trail for /fpl-review
calibration: predicted-at-date vs actual).

CLI:  python -m fpl_claude.models.projections [--from-snapshot YYYY-MM-DD]
          [--prior-snapshot PATH] [--horizon N] [--overlays PATH.json]
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..data import football_data
from ..data.fpl_api import PROJECT_ROOT, RAW_DIR, get_bootstrap, get_fixtures
from ..rules.engine import Ruleset
from . import minutes as minutes_model
from . import rates as rates_model
from .team import FixtureExpectation, TeamModel, fdr_expectation
from .xpts import ScoringMap, expected_points

PROJECTIONS_DIR = PROJECT_ROOT / "db" / "projections"
POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _load(from_snapshot: str | None) -> tuple[dict, list[dict]]:
    if from_snapshot:
        day_dir = RAW_DIR / from_snapshot
        return (
            json.loads((day_dir / "bootstrap.json").read_text()),
            json.loads((day_dir / "fixtures.json").read_text()),
        )
    return get_bootstrap(), get_fixtures()


def upcoming_gameweeks(bootstrap: dict, horizon: int) -> list[int]:
    """The next `horizon` unfinished gameweek ids, in order."""
    now = datetime.now(timezone.utc)
    ids = []
    for event in bootstrap["events"]:
        deadline = datetime.fromisoformat(event["deadline_time"].replace("Z", "+00:00"))
        if not event.get("finished") and deadline > now:
            ids.append(event["id"])
    return ids[:horizon]


def build_team_model() -> TeamModel | None:
    """Dixon-Coles from downloaded football-data results; None if unavailable."""
    try:
        results = football_data.load_results()
        if len(results) < 100:  # need a meaningful sample to fit
            return None
        return TeamModel.fit(results)
    except ImportError:  # penaltyblog not installed
        return None


def _fixture_expectation(
    fx: dict, teams: dict[int, dict], model: TeamModel | None
) -> FixtureExpectation:
    home, away = teams[fx["team_h"]]["name"], teams[fx["team_a"]]["name"]
    if model is not None and model.covers(home, away):
        return model.fixture(home, away)
    return fdr_expectation(fx.get("team_h_difficulty", 3), fx.get("team_a_difficulty", 3))


def build_projections(
    bootstrap: dict,
    fixtures: list[dict],
    ruleset: Ruleset | None = None,
    team_model: TeamModel | None = None,
    prior_bootstrap: dict | None = None,
    overlays: dict[int, dict[str, Any]] | None = None,
    horizon: int | None = None,
) -> pd.DataFrame:
    rules = ruleset or Ruleset.load()
    horizon = horizon or int(rules.policy("planning_horizon_gws"))
    decay = float(rules.policy("horizon_decay"))
    scoring = ScoringMap.from_ruleset(rules)

    gameweeks = upcoming_gameweeks(bootstrap, horizon)
    teams = {t["id"]: t for t in bootstrap["teams"]}

    # Fixture expectations per (gameweek, team): blanks yield no entry, doubles two.
    by_gw_team: dict[tuple[int, int], list[tuple[FixtureExpectation, bool]]] = {}
    sources: dict[int, set[str]] = {t: set() for t in teams}
    for fx in fixtures:
        if fx.get("event") in gameweeks and not fx.get("finished"):
            exp = _fixture_expectation(fx, teams, team_model)
            by_gw_team.setdefault((fx["event"], fx["team_h"]), []).append((exp, True))
            by_gw_team.setdefault((fx["event"], fx["team_a"]), []).append((exp, False))
            sources[fx["team_h"]].add(exp.source)
            sources[fx["team_a"]].add(exp.source)

    minutes_df = minutes_model.estimate_all(
        bootstrap,
        minutes_model.team_games_played(fixtures),
        priors=minutes_model.priors_from_bootstrap(prior_bootstrap) if prior_bootstrap else None,
        overlays=overlays,
    ).set_index("id")
    rates_df = rates_model.blend(
        rates_model.from_bootstrap(bootstrap),
        rates_model.from_bootstrap(prior_bootstrap) if prior_bootstrap else None,
    ).set_index("id")

    rows = []
    for p in bootstrap["elements"]:
        pid = int(p["id"])
        position = POSITION_BY_ELEMENT_TYPE[p["element_type"]]
        m_row = minutes_df.loc[pid]
        est = minutes_model.MinutesEstimate(
            player_id=pid,
            p_start=m_row["p_start"],
            p_cameo=m_row["p_cameo"],
            p60=m_row["p60"],
            exp_minutes=m_row["exp_minutes"],
            confidence=m_row["minutes_confidence"],
        )
        rates = rates_df.loc[pid].to_dict()

        per_gw: dict[str, float] = {}
        horizon_total = 0.0
        for i, gw in enumerate(gameweeks):
            gw_points = sum(
                expected_points(position, rates, est, exp, is_home, scoring)["total"]
                for exp, is_home in by_gw_team.get((gw, p["team"]), [])
            )
            per_gw[f"xpts_gw{gw}"] = round(gw_points, 2)
            horizon_total += gw_points * (decay**i)

        price = p["now_cost"] / 10.0
        rows.append(
            {
                "id": pid,
                "web_name": p["web_name"],
                "team": teams[p["team"]]["name"],
                "position": position,
                "price": price,
                "ownership_pct": float(p.get("selected_by_percent") or 0),
                **per_gw,
                "xpts_horizon": round(horizon_total, 2),
                "xpts_per_m": round(horizon_total / price, 3) if price else 0.0,
                "exp_minutes_gw": est.exp_minutes,
                "minutes_confidence": est.confidence,
                "low_sample": bool(rates.get("low_sample", False)),
                "team_model": "+".join(sorted(sources[p["team"]])) or "none",
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("xpts_horizon", ascending=False)
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", help="db/raw/ date dir (YYYY-MM-DD) instead of live API")
    parser.add_argument("--prior-snapshot", help="path to a previous season's bootstrap.json")
    parser.add_argument("--horizon", type=int, default=None)
    parser.add_argument("--overlays", help="JSON file: {player_id: {start_share, reason}}")
    args = parser.parse_args()

    bootstrap, fixtures = _load(args.from_snapshot)
    prior = json.loads(Path(args.prior_snapshot).read_text()) if args.prior_snapshot else None
    overlays = None
    if args.overlays:
        overlays = {int(k): v for k, v in json.loads(Path(args.overlays).read_text()).items()}

    df = build_projections(
        bootstrap,
        fixtures,
        team_model=build_team_model(),
        prior_bootstrap=prior,
        overlays=overlays,
        horizon=args.horizon,
    )

    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = PROJECTIONS_DIR / f"{date.today().isoformat()}.csv"
    df.to_csv(out, index=False)
    print(f"projections written: {out}")
    cols = ["web_name", "team", "position", "price", "xpts_horizon", "xpts_per_m"]
    print(df[cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()

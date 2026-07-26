"""Projections pipeline: minutes x rates x team model -> xPts per GW -> ranked table.

Glues the model layers together over the planning horizon from
config/rules (policies.planning_horizon_gws, policies.horizon_decay):

  1. bootstrap + fixtures (live, or --from-snapshot for point-in-time runs)
  2. minutes model v1 (+ optional priors from the prior payload, + overlays)
  3. per-90 rates blended with the same prior payload
  4. team model: Dixon-Coles if football-data results are on disk and
     penaltyblog is importable, FDR fallback otherwise (labeled per player)
  5. rules-driven scoring map -> per-GW xPts, decayed horizon total, xPts/£m

Output: DataFrame + CSV under db/projections/ (audit trail for /fpl-review
calibration: predicted-at-date vs actual).

Two ways to supply the prior, and picking the wrong one silently corrupts every
row:
  --prior-snapshot PATH      a bootstrap.json from EARLIER THIS SEASON. Joined
                             on element `id`, which is only stable WITHIN a
                             season.
  --prior-season-csv PATH    a COMPLETED season's vaastav players_raw.csv.
                             Remapped id-by-`code` through
                             data/season_bridge.py — the only correct way to
                             cross a season boundary, because FPL reassigns
                             every element id at rollover.

CLI:  python -m fpl_claude.models.projections [--from-snapshot YYYY-MM-DD]
          [--prior-snapshot PATH | --prior-season-csv PATH]
          [--horizon N] [--overlays PATH.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..console import enable_utf8_output
from ..data import football_data, season_bridge
from ..data.fpl_api import PROJECT_ROOT, RAW_DIR, get_bootstrap, get_fixtures
from ..rules.engine import Ruleset
from . import minutes as minutes_model
from . import rates as rates_model
from .team import FixtureExpectation, TeamModel, fdr_expectation
from .xpts import ScoringMap, expected_points

PROJECTIONS_DIR = PROJECT_ROOT / "db" / "projections"
POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _num_or_none(value: Any) -> float | None:
    """FPL API numerics arrive as strings ('4.5') or None; keep None as None so
    a benchmark column reads NaN (honestly absent) rather than a fake 0.0."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_print(text: str) -> None:
    """The Windows console is cp1252 and half the Premier League has an accent
    in his name (Gyokeres, Ekitike, Joao Pedro) — printing the ranked table
    raised UnicodeEncodeError and killed a run that had already done all the
    work. Transliterate for the console only; the CSV keeps real names."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        text = text.encode(encoding, errors="replace").decode(encoding)
    print(text)


def _load(from_snapshot: str | None) -> tuple[dict, list[dict]]:
    if from_snapshot:
        day_dir = RAW_DIR / from_snapshot
        # encoding is explicit: the console default on Windows is cp1252 and the
        # bootstrap is full of accented names (Gyokeres, Ekitike, Joao Pedro).
        return (
            json.loads((day_dir / "bootstrap.json").read_text(encoding="utf-8")),
            json.loads((day_dir / "fixtures.json").read_text(encoding="utf-8")),
        )
    return get_bootstrap(), get_fixtures()


def _warn_if_ids_reassigned(current: dict, prior: dict) -> None:
    """A --prior-snapshot from a DIFFERENT season joins garbage to every row.

    Both payloads carry `code` (the permanent player key), so we can detect the
    mismatch instead of shipping silently wrong projections: if the id->code map
    disagrees on most shared ids, the snapshot is from another season."""
    cur = {int(p["id"]): p.get("code") for p in current["elements"] if p.get("code")}
    old = {int(p["id"]): p.get("code") for p in prior.get("elements", []) if p.get("code")}
    shared = set(cur) & set(old)
    if len(shared) < 50:
        return
    agree = sum(1 for pid in shared if cur[pid] == old[pid])
    if agree / len(shared) < 0.9:
        print(
            f"WARNING: --prior-snapshot ids match the current bootstrap for only "
            f"{agree}/{len(shared)} players — this looks like a DIFFERENT season, "
            f"whose element ids FPL has reassigned. Every prior would be attached "
            f"to the wrong player. Use --prior-season-csv instead."
        )


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
    minutes_v2: Mapping[int, minutes_model.ModelMinutes] | None = None,
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

    team_games = minutes_model.team_games_played(fixtures)
    priors = minutes_model.priors_from_bootstrap(prior_bootstrap) if prior_bootstrap else None
    minutes_df = minutes_model.estimate_all(
        bootstrap, team_games, priors=priors, overlays=overlays, model=minutes_v2
    ).set_index("id")
    # Overlays are TIME-SCOPED: an entry may carry duration_gws (how many
    # horizon GWs the news covers — 1 for a this-week knock, more for longer
    # absences; omitted = whole horizon, the safe default for ACLs/departures).
    # Beyond its duration the player projects on his CLEAN estimate — a
    # one-week doubt priced as an 8-GW absence inflated forced-move EV ~4x
    # and drove three phantom sells in four backtest weeks.
    clean_df = (
        minutes_model.estimate_all(
            bootstrap, team_games, priors=priors, model=minutes_v2
        ).set_index("id")
        if overlays
        else minutes_df
    )
    element_type = pd.Series(
        {int(p["id"]): int(p["element_type"]) for p in bootstrap["elements"]}
    )
    rates_df = rates_model.shrink_newcomers(
        rates_model.blend(
            rates_model.from_bootstrap(bootstrap),
            rates_model.from_bootstrap(prior_bootstrap) if prior_bootstrap else None,
        ),
        element_type,
    ).set_index("id")

    def _estimate_from(df: pd.DataFrame, pid: int) -> minutes_model.MinutesEstimate:
        m_row = df.loc[pid]
        return minutes_model.MinutesEstimate(
            player_id=pid,
            p_start=m_row["p_start"],
            p_cameo=m_row["p_cameo"],
            p60=m_row["p60"],
            exp_minutes=m_row["exp_minutes"],
            confidence=m_row["minutes_confidence"],
        )

    rows = []
    for p in bootstrap["elements"]:
        pid = int(p["id"])
        position = POSITION_BY_ELEMENT_TYPE[p["element_type"]]
        est = _estimate_from(minutes_df, pid)
        overlay = (overlays or {}).get(pid)
        duration = len(gameweeks)
        if overlay is not None and overlay.get("duration_gws") is not None:
            duration = max(0, int(overlay["duration_gws"]))
        rates = rates_df.loc[pid].to_dict()

        # Set-piece duty: point-in-time live, season-end proxy in the backtest.
        # `penalties_order == 1` is the designated taker; the xPts penalty term
        # reads pen_taker (+ optional overlay pen_boost for a duty change).
        pen_order = p.get("penalties_order")
        is_pen_taker = pen_order == 1
        rates["pen_taker"] = is_pen_taker
        rates["pen_boost"] = float(overlay.get("pen_boost", 0.0)) if overlay else 0.0
        is_sp_taker = 1 in (
            p.get("corners_and_indirect_freekicks_order"),
            p.get("direct_freekicks_order"),
        )

        per_gw: dict[str, float] = {}
        horizon_total = 0.0
        for i, gw in enumerate(gameweeks):
            gw_est = est if i < duration else _estimate_from(clean_df, pid)
            gw_points = sum(
                expected_points(position, rates, gw_est, exp, is_home, scoring)["total"]
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
                # FPL's own next-GW expected points: a free external benchmark
                # for /fpl-review calibration and a captaincy sanity check, never
                # a model input. NaN when absent (backtest archive has no
                # point-in-time ep_next).
                "ep_next": _num_or_none(p.get("ep_next")),
                "is_pen_taker": bool(is_pen_taker),
                "is_set_piece_taker": bool(is_sp_taker),
                "team_model": "+".join(sorted(sources[p["team"]])) or "none",
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("xpts_horizon", ascending=False)
        .reset_index(drop=True)
    )


def main() -> None:
    enable_utf8_output()  # player names carry accents; cp1252 misses some of them
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", help="db/raw/ date dir (YYYY-MM-DD) instead of live API")
    prior_group = parser.add_mutually_exclusive_group()
    prior_group.add_argument(
        "--prior-snapshot",
        help="bootstrap.json from EARLIER THIS SEASON (joined on element id)",
    )
    prior_group.add_argument(
        "--prior-season-csv",
        help="a COMPLETED season's vaastav players_raw.csv; ids remapped via `code`",
    )
    parser.add_argument(
        "--min-prior-minutes",
        type=int,
        default=0,
        help="with --prior-season-csv: ignore prior rows thinner than this (an "
             "injured/loaned-out player's row of zeros is absence, not evidence)",
    )
    parser.add_argument("--horizon", type=int, default=None)
    parser.add_argument(
        "--overlays",
        help="JSON file: {player_id: {start_share, reason, [duration_gws], [pen_boost]}}",
    )
    args = parser.parse_args()

    bootstrap, fixtures = _load(args.from_snapshot)

    prior = None
    if args.prior_season_csv:
        prior = season_bridge.prior_bootstrap_from_vaastav(
            bootstrap, args.prior_season_csv, min_minutes=args.min_prior_minutes
        )
        print(season_bridge.coverage(bootstrap, prior).to_text())
        print()
    elif args.prior_snapshot:
        prior = json.loads(Path(args.prior_snapshot).read_text(encoding="utf-8"))
        _warn_if_ids_reassigned(bootstrap, prior)

    overlays = None
    if args.overlays:
        raw_overlays = Path(args.overlays).read_text(encoding="utf-8")
        overlays = {int(k): v for k, v in json.loads(raw_overlays).items()}

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
    _safe_print(df[cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()

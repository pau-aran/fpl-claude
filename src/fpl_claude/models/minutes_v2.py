"""Minutes model v2 — LightGBM on vaastav history, same interface as v1.

Minutes are the single biggest edge in this project (CLAUDE.md rule 2): most FPL
points are lost to benchings, not to bad scoring-rate estimates. v1 in
`minutes.py` reads one number off the API — season starts / team games — and
shrinks it toward a prior. That is a *level* estimator: it knows Gabriel starts
80% of the time, but it cannot know that this particular week is his third game
in eight days, that his club plays a European tie on Wednesday, or that he has
started the last six on the trot after a slow August. Those are exactly the
weeks the market misprices, and they are the weeks a bench-order or a captain
call gets decided on.

v2 replaces `_start_share` and `_p60_given_start` with gradient-boosted models
trained on the vaastav/Fantasy-Premier-League archive. Four heads, deliberately
chosen over one minutes regressor:

  p_start   P(named in the XI)         binary LightGBM
  p_play    P(any minutes)             binary LightGBM
  p60       P(60+ minutes)             binary LightGBM
  mins|start E[minutes | started]      LightGBM regressor, started rows only

Expected minutes is then the mixture `p_start*E[min|start] + p_cameo*cameo_min`
rather than a direct regression on minutes. The minutes distribution is
trimodal — a spike at 0 (unused), a bump around 15-25 (cameo), a mass at
85-90 (full game) — and a squared-error regressor on that target smears its
predictions into the empty middle, where no observation ever lands. The mixture
keeps each head on a target it can actually fit, and it is the decomposition the
downstream xPts layer wants anyway: appearance points key off p_play/p60, clean
sheets off p60, and the optimizer's bench order off p_start.

Point-in-time discipline (non-negotiable — this repo's backtests are
leakage-audited): every history feature for gameweek n is built from GW-level
aggregates strictly before n. Not "before this kickoff" — before the *gameweek*,
because in a double gameweek both fixtures sit behind one deadline and knowing
what happened in the first would be knowledge the manager did not have. The
fixture *calendar* (dates, opponents, FDR, congestion) is published months
ahead and is fair game.

What v2 deliberately does NOT model:
  - availability. The archive carries no historical injury flags (`status` is
    always "a" in a replay), so a model trained on it cannot learn them. Flags
    stay where v1 put them: an explicit multiplier in `minutes.estimate`, on top
    of the model's share.
  - the news overlay. It still wins, always, over both v1 and v2 — a written
    press-conference read beats any number of trees (CLAUDE.md rule 4).
  - nationality, so the AFCON flag can only move the base rate, not identify who
    leaves. See `reports/models/minutes-v2.md` for how badly that limits it.

Cold start is handled by omission: a player with no gameweek history this season
and no prior-season record is left OUT of the prediction mapping entirely, so
`minutes.estimate` falls through to the v1 prior path. A new signing is a real
unknown that the overlay must resolve from news; inventing a confident number
for him would be worse than saying so.

Everything degrades: no lightgbm, no artifact, no problem — `load_model` returns
None and the pipeline is byte-identical to v1.

CLI:
    PYTHONPATH=src python -m fpl_claude.models.minutes_v2 --train \\
        --data-root db/vaastav --out db/models/minutes_v2.joblib \\
        --metrics reports/models/minutes-v2-metrics.json
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_claude.models.minutes import DEFAULT_CAMEO_MINUTES, ModelMinutes

SEED = 20262027

# Seasons the archive carries a `starts` column for. Before 2022-23 vaastav's
# merged_gw has minutes but no starts, and "started" cannot be recovered from
# minutes without contaminating the target, so those seasons are unusable for
# the p_start head and are excluded wholesale rather than half-used.
TRAIN_SEASONS = ("2022-23", "2023-24", "2024-25")
HOLDOUT_SEASON = "2025-26"
# FPL only shipped the `starts` field partway through 2022-23: every merged_gw
# row before GW16 that season reads starts=0, so ~47% of its "substitutes"
# played 60+ minutes. Training the p_start head on that would be fitting a
# fabricated target, and the rolling start-share features would inherit the lie.
# We therefore treat 2022-23 as beginning at GW16 — the season's history simply
# starts there, which the `hist_games`/`gw` features already express.
SEASON_MIN_GW = {"2022-23": 16}

PRIOR_OF = {
    "2022-23": "2021-22",
    "2023-24": "2022-23",
    "2024-25": "2023-24",
    "2025-26": "2024-25",
}

POSITION_TO_ELEMENT_TYPE = {"GK": 1, "GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}

FULL_SEASON_GAMES = 38
CAMEO_CEILING = 60  # a "cameo" is an appearance short of the 60' scoring gate
MIDWEEK_DAYS = {1, 2, 3}  # Tue/Wed/Thu kickoffs

# AFCON tournament windows, plus a week of pre-departure (squads leave before the
# opening game). Only two of these fall inside seasons we can train on, which is
# why the flag is weak — see the evaluation report.
AFCON_WINDOWS: dict[str, tuple[str, str]] = {
    "2021-22": ("2022-01-03", "2022-02-06"),
    "2023-24": ("2024-01-06", "2024-02-11"),
    "2025-26": ("2025-12-14", "2026-01-18"),
}

# UEFA club-competition periods within a season, as month/day windows on the
# season's two calendar years. Europe is dark in August, over Christmas and
# through January; a "Euro week" outside these can't exist.
UEFA_PERIODS = ((9, 10, 12, 22), (2, 8, 6, 5))  # (start_m, start_d, end_m, end_d)

EURO_QUALIFYING_RANK = 7  # prior-season top-7 ≈ the clubs with midweek Europe

INTL_BREAK_GAP_DAYS = 9  # league-wide fixture gap that means a FIFA window

FEATURES: tuple[str, ...] = (
    # what he has been doing
    "hist_games",
    "start_share_3",
    "start_share_5",
    "start_share_10",
    "start_share_season",
    "mins_mean_3",
    "mins_mean_5",
    "mins_mean_10",
    "mins_last",
    "started_last",
    "starts_streak",
    "benched_streak",
    "cameo_rate",
    "p60_rate_season",
    "blank_rate_5",
    "prior_start_share",
    "prior_mins_per_game",
    # who he is
    "element_type",
    "price",
    "price_rank_team_pos",
    "price_share_team_pos",
    "selected_log",
    # this fixture
    "gw",
    "was_home",
    "opp_difficulty",
    "team_fixtures_this_gw",
    # congestion / calendar
    "days_since_prev",
    "days_to_next",
    "team_fix_last_7",
    "team_fix_last_14",
    "team_fix_next_7",
    "team_fix_next_14",
    "is_midweek",
    "league_gap_prev",
    "intl_break_prev",
    "euro_club",
    "uefa_window",
    "euro_week",
    "afcon_window",
)

CATEGORICAL: tuple[str, ...] = ("element_type",)

TARGETS = ("y_start", "y_play", "y_p60", "y_minutes")


# --------------------------------------------------------------------- features


def _season_years(season: str) -> tuple[int, int]:
    """('2024-25') -> (2024, 2025)."""
    start = int(season[:4])
    return start, start + 1


def _afcon_mask(kickoff: pd.Series, season: str) -> pd.Series:
    window = AFCON_WINDOWS.get(season)
    if window is None:
        return pd.Series(0, index=kickoff.index, dtype="int8")
    lo, hi = (pd.Timestamp(w, tz="UTC") for w in window)
    return ((kickoff >= lo) & (kickoff <= hi)).astype("int8")


def _uefa_mask(kickoff: pd.Series, season: str) -> pd.Series:
    y0, y1 = _season_years(season)
    mask = pd.Series(False, index=kickoff.index)
    for i, (sm, sd, em, ed) in enumerate(UEFA_PERIODS):
        year = y0 if i == 0 else y1
        lo = pd.Timestamp(date(year, sm, sd), tz="UTC")
        hi = pd.Timestamp(date(year, em, ed), tz="UTC")
        mask |= (kickoff >= lo) & (kickoff <= hi)
    return mask.astype("int8")


def _prior_table_rank(prior_fixtures: pd.DataFrame, prior_teams: pd.DataFrame) -> dict[str, int]:
    """Final PL table position per team NAME from a season's fixture results.

    Used only as a proxy for "does this club play midweek in Europe next
    season", which is knowable before a ball is kicked — no leakage.
    """
    done = prior_fixtures.dropna(subset=["team_h_score", "team_a_score"])
    names = prior_teams.set_index("id")["name"].to_dict()
    points: dict[str, int] = {n: 0 for n in names.values()}
    goal_diff: dict[str, int] = {n: 0 for n in names.values()}
    for f in done.itertuples():
        h, a = names.get(int(f.team_h)), names.get(int(f.team_a))
        if h is None or a is None:
            continue
        hg, ag = int(f.team_h_score), int(f.team_a_score)
        goal_diff[h] += hg - ag
        goal_diff[a] += ag - hg
        if hg > ag:
            points[h] += 3
        elif ag > hg:
            points[a] += 3
        else:
            points[h] += 1
            points[a] += 1
    order = sorted(points, key=lambda n: (-points[n], -goal_diff[n], n))
    return {name: rank for rank, name in enumerate(order, start=1)}


def _team_calendar(fixtures: pd.DataFrame) -> pd.DataFrame:
    """Per (team, fixture) congestion features from the published schedule.

    The fixture calendar is public months ahead, so counting a team's matches in
    the next 14 days is not leakage — it is what a manager reads off the app.
    """
    rows = []
    for f in fixtures.itertuples():
        if pd.isna(f.event) or pd.isna(f.kickoff_time):
            continue
        rows.append({"team": int(f.team_h), "fixture": int(f.id), "kickoff": f.kickoff_time})
        rows.append({"team": int(f.team_a), "fixture": int(f.id), "kickoff": f.kickoff_time})
    cal = pd.DataFrame(rows)
    if cal.empty:
        return cal
    cal["kickoff"] = pd.to_datetime(cal["kickoff"], utc=True, format="mixed")
    cal = cal.sort_values(["team", "kickoff"]).reset_index(drop=True)

    grp = cal.groupby("team")["kickoff"]
    cal["days_since_prev"] = (cal["kickoff"] - grp.shift(1)).dt.total_seconds() / 86400.0
    cal["days_to_next"] = (grp.shift(-1) - cal["kickoff"]).dt.total_seconds() / 86400.0

    # Match counts in rolling date windows around each fixture (excluding itself).
    counts = {f"team_fix_{w}": [] for w in ("last_7", "last_14", "next_7", "next_14")}
    for _, g in cal.groupby("team", sort=False):
        k = g["kickoff"].dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")
        for i, t in enumerate(k):
            delta = (k - t) / np.timedelta64(1, "D")
            counts["team_fix_last_7"].append(int(((delta < 0) & (delta >= -7)).sum()))
            counts["team_fix_last_14"].append(int(((delta < 0) & (delta >= -14)).sum()))
            counts["team_fix_next_7"].append(int(((delta > 0) & (delta <= 7)).sum()))
            counts["team_fix_next_14"].append(int(((delta > 0) & (delta <= 14)).sum()))
    for col, values in counts.items():
        cal[col] = values

    # League-wide gap: days since the last date ANY PL fixture was played. A gap
    # of 9+ days is a FIFA international window (or a weather-wrecked calendar).
    days = np.sort(cal["kickoff"].dt.normalize().unique())
    day_index = pd.Series(range(len(days)), index=days)
    own_day = cal["kickoff"].dt.normalize()
    prev_pos = own_day.map(day_index) - 1
    prev_day = pd.Series(
        [days[int(p)] if p >= 0 else pd.NaT for p in prev_pos], index=cal.index
    )
    cal["league_gap_prev"] = (own_day - prev_day).dt.total_seconds() / 86400.0
    cal["intl_break_prev"] = (cal["league_gap_prev"] >= INTL_BREAK_GAP_DAYS).astype("int8")

    cal["is_midweek"] = cal["kickoff"].dt.dayofweek.isin(MIDWEEK_DAYS).astype("int8")
    return cal.drop(columns=["kickoff"])


def _gw_history(merged: pd.DataFrame) -> pd.DataFrame:
    """GW-level per-player history, shifted so row GW n sees only GWs < n.

    Aggregating to the GW *before* rolling is the leakage guard for double
    gameweeks: both fixtures sit behind one deadline, so fixture 2 must not know
    fixture 1's minutes.
    """
    gw = (
        merged.groupby(["element", "GW"], as_index=False)
        .agg(
            gw_starts=("starts", "sum"),
            gw_minutes=("minutes", "sum"),
            gw_fixtures=("minutes", "size"),
            gw_p60=("minutes", lambda s: float((s >= 60).mean())),
            gw_cameo=("minutes", lambda s: float(((s > 0) & (s < CAMEO_CEILING)).mean())),
            gw_blank=("minutes", lambda s: float((s == 0).mean())),
        )
        .sort_values(["element", "GW"])
        .reset_index(drop=True)
    )
    gw["gw_start_rate"] = gw["gw_starts"] / gw["gw_fixtures"]
    gw["gw_mins_per_fix"] = gw["gw_minutes"] / gw["gw_fixtures"]

    g = gw.groupby("element", sort=False)
    gw["hist_games"] = g.cumcount()
    for k in (3, 5, 10):
        gw[f"start_share_{k}"] = g["gw_start_rate"].transform(
            lambda s, k=k: s.shift(1).rolling(k, min_periods=1).mean()
        )
        gw[f"mins_mean_{k}"] = g["gw_mins_per_fix"].transform(
            lambda s, k=k: s.shift(1).rolling(k, min_periods=1).mean()
        )
    gw["start_share_season"] = g["gw_start_rate"].transform(
        lambda s: s.shift(1).expanding().mean()
    )
    gw["cameo_rate"] = g["gw_cameo"].transform(lambda s: s.shift(1).expanding().mean())
    gw["p60_rate_season"] = g["gw_p60"].transform(lambda s: s.shift(1).expanding().mean())
    gw["blank_rate_5"] = g["gw_blank"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=1).mean()
    )
    gw["mins_last"] = g["gw_mins_per_fix"].shift(1)
    gw["started_last"] = (g["gw_start_rate"].shift(1) >= 1.0).astype("float")
    gw.loc[gw["hist_games"] == 0, "started_last"] = np.nan

    # Cumulative season totals as v1 would have read them off the bootstrap —
    # kept so the v1 baseline can be scored on exactly the same rows.
    gw["cum_starts"] = g["gw_starts"].transform(lambda s: s.shift(1).cumsum())
    gw["cum_minutes"] = g["gw_minutes"].transform(lambda s: s.shift(1).cumsum())

    started = gw["gw_start_rate"] >= 1.0
    gw["starts_streak"] = _prior_streak(gw["element"], started)
    gw["benched_streak"] = _prior_streak(gw["element"], ~started)
    return gw


def _prior_streak(keys: pd.Series, flag: pd.Series) -> pd.Series:
    """Consecutive prior True runs ending at the row before each row."""
    prev = flag.groupby(keys, sort=False).shift(1).fillna(False).astype(bool)
    run = prev.groupby([keys, (~prev).cumsum()], sort=False).cumsum()
    return run.astype("float")


def build_features(
    merged: pd.DataFrame,
    fixtures: pd.DataFrame,
    teams: pd.DataFrame,
    players: pd.DataFrame,
    prior_players: pd.DataFrame | None,
    prior_fixtures: pd.DataFrame | None,
    prior_teams: pd.DataFrame | None,
    season: str,
) -> pd.DataFrame:
    """One feature row per (player, fixture) for a whole season.

    Building the season in one pass and slicing GW n out of it is *identical* to
    building only GWs < n, because every history column is shifted at GW
    granularity — `tests/test_minutes_v2.py` asserts exactly that.
    """
    m = merged.copy()
    m["kickoff"] = pd.to_datetime(m["kickoff_time"], utc=True, format="mixed")
    m["element"] = m["element"].astype(int)
    m["GW"] = m["GW"].astype(int)
    m["minutes"] = m["minutes"].fillna(0).astype(int)
    m["starts"] = m["starts"].fillna(0).astype(int)
    m["element_type"] = m["position"].map(POSITION_TO_ELEMENT_TYPE)
    m = m[m["element_type"].notna()].copy()  # drop assistant-manager pseudo-players
    m["element_type"] = m["element_type"].astype(int)

    hist = _gw_history(m)
    hist_cols = [c for c in hist.columns if c not in ("gw_starts", "gw_minutes", "gw_fixtures")]
    out = m.merge(hist[hist_cols], on=["element", "GW"], how="left")

    # ---- fixture context (schedule-derived: known before the deadline)
    fx = fixtures.copy()
    fx = fx[fx["event"].notna()]
    fx_diff = fx.set_index("id")[["team_h_difficulty", "team_a_difficulty", "team_h", "team_a"]]
    out["was_home"] = out["was_home"].astype(bool)
    out = out.join(fx_diff, on="fixture")
    out["opp_difficulty"] = np.where(
        out["was_home"], out["team_h_difficulty"], out["team_a_difficulty"]
    )
    out["team_id"] = np.where(out["was_home"], out["team_h"], out["team_a"])

    cal = _team_calendar(fx)
    out = out.merge(
        cal, left_on=["team_id", "fixture"], right_on=["team", "fixture"], how="left",
        suffixes=("", "_cal"),
    )

    # ---- price / ownership at this gameweek
    out["price"] = out["value"] / 10.0
    grp = out.groupby(["GW", "team_id", "element_type"])["value"]
    out["price_rank_team_pos"] = grp.rank(method="min", ascending=False)
    out["price_share_team_pos"] = out["value"] / grp.transform("max")
    sel = out.sort_values(["element", "GW"]).groupby("element")["selected"].shift(1)
    out["selected_log"] = np.log10(1.0 + sel.fillna(0.0))

    # ---- calendar flags
    out["afcon_window"] = _afcon_mask(out["kickoff"], season)
    out["uefa_window"] = _uefa_mask(out["kickoff"], season)
    if prior_fixtures is not None and prior_teams is not None:
        rank = _prior_table_rank(prior_fixtures, prior_teams)
        team_name = teams.set_index("id")["name"].to_dict()
        euro = {
            int(tid): int(rank.get(name, 99) <= EURO_QUALIFYING_RANK)
            for tid, name in team_name.items()
        }
        out["euro_club"] = out["team_id"].map(euro).fillna(0).astype("int8")
    else:
        out["euro_club"] = 0
    out["euro_week"] = (out["euro_club"] * out["uefa_window"]).astype("int8")

    out["team_fixtures_this_gw"] = out.groupby(["GW", "team_id"])["fixture"].transform("nunique")
    out["gw"] = out["GW"]

    # ---- prior-season record (season-final, so valid from GW1 onward)
    prior = _prior_season_record(players, prior_players)
    out["prior_start_share"] = out["element"].map(prior.get("start_share", {}))
    out["prior_mins_per_game"] = out["element"].map(prior.get("mins_per_game", {}))
    out["prior_games"] = out["element"].map(prior.get("games", {})).fillna(0.0)

    # ---- targets (scoring only, never a feature)
    out["y_start"] = (out["starts"] >= 1).astype(int)
    out["y_play"] = (out["minutes"] > 0).astype(int)
    out["y_p60"] = (out["minutes"] >= 60).astype(int)
    out["y_minutes"] = out["minutes"].astype(float)

    # team_games_before: PL games the player's club had completed before this GW.
    played = (
        fx[fx["event"] < out["GW"].max() + 1]
        .melt(id_vars=["event"], value_vars=["team_h", "team_a"], value_name="team_id")
        .groupby(["team_id", "event"], as_index=False)
        .size()
    )
    played = played.sort_values(["team_id", "event"])
    played["team_games_before"] = (
        played.groupby("team_id")["size"].transform(lambda s: s.shift(1).cumsum()).fillna(0)
    )
    out = out.merge(
        played[["team_id", "event", "team_games_before"]],
        left_on=["team_id", "GW"], right_on=["team_id", "event"], how="left",
    )
    out["team_games_before"] = out["team_games_before"].fillna(0)

    out["season"] = season
    out["is_cold_start"] = ((out["hist_games"] == 0) & (out["prior_games"] == 0)).astype(int)
    for col in ("cum_starts", "cum_minutes"):
        out[col] = out[col].fillna(0.0)
    return out


def _prior_season_record(
    players: pd.DataFrame, prior_players: pd.DataFrame | None
) -> dict[str, dict[int, float]]:
    """Previous season's start share / minutes per game, keyed by THIS season's
    player id via the cross-season `code`. FPL ids reset each summer; codes do
    not. A player without a prior row is a genuine unknown, not a zero."""
    if prior_players is None or "code" not in prior_players.columns:
        return {}
    code_to_id = {int(p.code): int(p.id) for p in players.itertuples()}
    start_share: dict[int, float] = {}
    mins_pg: dict[int, float] = {}
    games: dict[int, float] = {}
    has_starts = "starts" in prior_players.columns
    for p in prior_players.to_dict("records"):
        pid = code_to_id.get(int(p["code"]))
        if pid is None:
            continue
        minutes = float(p.get("minutes") or 0)
        mins_pg[pid] = minutes / FULL_SEASON_GAMES
        games[pid] = 1.0 if minutes > 0 else 0.0
        if has_starts:
            start_share[pid] = min(1.0, float(p.get("starts") or 0) / FULL_SEASON_GAMES)
    return {"start_share": start_share, "mins_per_game": mins_pg, "games": games}


def dataset_for_season(root: Path | str, season: str, prior: str | None = None) -> pd.DataFrame:
    """Feature frame for one archived season, read through `backtest.SeasonStore`."""
    from fpl_claude.backtest.data import SeasonStore

    prior = prior or PRIOR_OF.get(season, season)
    store = SeasonStore(Path(root), season=season, prior=prior)
    merged = store.merged
    first_gw = SEASON_MIN_GW.get(season)
    if first_gw is not None:
        merged = merged[merged["GW"] >= first_gw]
    return build_features(
        merged=merged,
        fixtures=store.fixtures,
        teams=store.teams,
        players=store.players,
        prior_players=store.prior_players,
        prior_fixtures=store.prior_fixtures,
        prior_teams=store.prior_teams,
        season=season,
    )


def history_frame_from_element_summaries(
    summaries: Mapping[int, dict[str, Any]], bootstrap: dict[str, Any]
) -> pd.DataFrame:
    """Adapt live `element-summary/{id}/` payloads into a merged_gw-shaped frame.

    The live pipeline has no vaastav CSV; it has one history list per player.
    The columns differ only in naming, so the same feature builder serves both
    the backtest replay and a real deadline.
    """
    position = {
        int(p["id"]): {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}[int(p["element_type"])]
        for p in bootstrap["elements"]
    }
    rows = []
    for pid, payload in summaries.items():
        for h in payload.get("history", []):
            rows.append(
                {
                    "element": int(pid),
                    "GW": int(h["round"]),
                    "fixture": int(h["fixture"]),
                    "minutes": int(h.get("minutes") or 0),
                    "starts": int(h.get("starts") or 0),
                    "value": int(h.get("value") or 0),
                    "selected": int(h.get("selected") or 0),
                    "was_home": bool(h["was_home"]),
                    "opponent_team": int(h["opponent_team"]),
                    "kickoff_time": h["kickoff_time"],
                    "position": position.get(int(pid), "MID"),
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------- model


@dataclass
class MinutesModelV2:
    """Trained heads plus the metadata inference needs. Pure data — the LightGBM
    boosters are the only heavy objects, and nothing here imports lightgbm at
    module level so a lightgbm-less environment can still import this file."""

    boosters: dict[str, Any]
    features: Sequence[str] = FEATURES
    cameo_minutes: float = DEFAULT_CAMEO_MINUTES
    meta: dict[str, Any] = field(default_factory=dict)

    def predict_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        """Raw head outputs for a feature frame, coherence-corrected.

        Trees do not know that P(60+) <= P(any minutes); when they disagree it is
        always because one head is extrapolating, so we clamp rather than let an
        incoherent triple reach the optimizer.
        """
        Xf = X.reindex(columns=list(self.features))
        for col in CATEGORICAL:
            if col in Xf.columns:
                Xf[col] = Xf[col].astype("category")
        p_start = np.clip(self.boosters["p_start"].predict(Xf), 0.0, 1.0)
        p_play = np.clip(self.boosters["p_play"].predict(Xf), 0.0, 1.0)
        p60 = np.clip(self.boosters["p60"].predict(Xf), 0.0, 1.0)
        mins_start = np.clip(self.boosters["mins_given_start"].predict(Xf), 1.0, 90.0)

        p_play = np.maximum(p_play, p_start)
        p60 = np.minimum(p60, p_play)
        p_cameo = np.maximum(0.0, p_play - p_start)
        exp_minutes = np.clip(
            p_start * mins_start + p_cameo * self.cameo_minutes, 0.0, 90.0
        )
        return pd.DataFrame(
            {
                "p_start": p_start,
                "p_cameo": p_cameo,
                "p_play": p_play,
                "p60": p60,
                "mins_given_start": mins_start,
                "exp_minutes": exp_minutes,
            },
            index=X.index,
        )

    def predict_gw(self, features_gw: pd.DataFrame) -> dict[int, ModelMinutes]:
        """Per-player `ModelMinutes` for one gameweek's feature rows.

        Cold-start rows are dropped, not predicted: absent from the mapping,
        `minutes.estimate` uses the v1 prior path and labels itself "prior".
        Double gameweeks collapse to the mean over the player's fixtures — the
        estimate is per-fixture by contract, and the projections layer multiplies
        it across the GW's fixtures itself.
        """
        rows = features_gw[features_gw["is_cold_start"] == 0]
        if rows.empty:
            return {}
        preds = self.predict_frame(rows)
        preds["element"] = rows["element"].to_numpy()
        agg = preds.groupby("element").mean()
        out: dict[int, ModelMinutes] = {}
        for pid, r in agg.iterrows():
            share = float(r["p_start"])
            p60_given_start = float(r["p60"] / share) if share > 1e-6 else 0.0
            out[int(pid)] = ModelMinutes(
                start_share=share,
                cameo_share=float(r["p_cameo"]),
                p60_given_start=min(1.0, max(0.0, p60_given_start)),
                minutes_given_start=float(r["mins_given_start"]),
                cameo_minutes=self.cameo_minutes,
            )
        return out

    def save(self, path: Path | str) -> Path:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "boosters": {k: v.model_to_string() for k, v in self.boosters.items()},
                "features": list(self.features),
                "cameo_minutes": self.cameo_minutes,
                "meta": self.meta,
            },
            path,
        )
        return path


DEFAULT_ARTIFACT = Path("db/models/minutes_v2.joblib")


def load_model(path: Path | str | None = None) -> MinutesModelV2 | None:
    """Trained v2, or None when lightgbm/joblib/the artifact is missing.

    Returning None rather than raising is the whole graceful-degradation
    contract: a fresh clone with no artifact runs the v1 heuristic and every
    test and backtest still passes.
    """
    path = Path(path) if path is not None else DEFAULT_ARTIFACT
    if not path.exists():
        return None
    try:
        import joblib
        import lightgbm as lgb
    except ImportError:
        return None
    try:
        blob = joblib.load(path)
        boosters = {k: lgb.Booster(model_str=v) for k, v in blob["boosters"].items()}
    except Exception:  # noqa: BLE001 — a stale artifact must never break a deadline
        return None
    return MinutesModelV2(
        boosters=boosters,
        features=tuple(blob.get("features", FEATURES)),
        cameo_minutes=float(blob.get("cameo_minutes", DEFAULT_CAMEO_MINUTES)),
        meta=blob.get("meta", {}),
    )


# -------------------------------------------------------------------- training

BASE_PARAMS: dict[str, Any] = {
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_child_samples": 200,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "verbose": -1,
    "seed": SEED,
    "deterministic": True,
    "num_threads": 4,
}
NUM_ROUNDS = 1500
EARLY_STOPPING = 60
VALID_TAIL_GWS = 8  # last N GWs of the final training season = inner validation


def _matrix(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=list(FEATURES)).copy()
    for col in CATEGORICAL:
        X[col] = X[col].astype("category")
    return X


def _fit_head(
    train: pd.DataFrame, valid: pd.DataFrame, target: str, objective: str, metric: str
) -> Any:
    import lightgbm as lgb

    params = {**BASE_PARAMS, "objective": objective, "metric": metric}
    dtrain = lgb.Dataset(_matrix(train), label=train[target], free_raw_data=False)
    dvalid = lgb.Dataset(_matrix(valid), label=valid[target], reference=dtrain)
    return lgb.train(
        params,
        dtrain,
        num_boost_round=NUM_ROUNDS,
        valid_sets=[dvalid],
        callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
    )


def train(
    train_df: pd.DataFrame, valid_df: pd.DataFrame, cameo_minutes: float | None = None
) -> MinutesModelV2:
    """Fit the four heads. `valid_df` is only for early stopping — the real
    holdout season never enters this function."""
    boosters = {
        "p_start": _fit_head(train_df, valid_df, "y_start", "binary", "binary_logloss"),
        "p_play": _fit_head(train_df, valid_df, "y_play", "binary", "binary_logloss"),
        "p60": _fit_head(train_df, valid_df, "y_p60", "binary", "binary_logloss"),
    }
    # Squared error, not absolute error, and deliberately so: xPts needs the
    # conditional MEAN. An L1 head returns the median, which for this target is
    # 90 for nearly every starter, and the mixture then over-predicts expected
    # minutes by ~1.2/row. See the evaluation report — the L1 variant posts a
    # flattering MAE and a worse RMSE and bias, which is the wrong trade for a
    # number that gets multiplied by a scoring rate.
    started = train_df[train_df["y_start"] == 1]
    started_valid = valid_df[valid_df["y_start"] == 1]
    boosters["mins_given_start"] = _fit_head(
        started, started_valid, "y_minutes", "regression", "l2"
    )
    if cameo_minutes is None:
        cameo = train_df[(train_df["y_start"] == 0) & (train_df["y_play"] == 1)]["y_minutes"]
        cameo_minutes = float(cameo.mean()) if len(cameo) else DEFAULT_CAMEO_MINUTES
    return MinutesModelV2(
        boosters=boosters,
        cameo_minutes=round(cameo_minutes, 2),
        meta={
            "seed": SEED,
            "train_rows": len(train_df),
            "valid_rows": len(valid_df),
            "train_seasons": sorted(train_df["season"].unique().tolist()),
            "best_iteration": {k: int(v.best_iteration or 0) for k, v in boosters.items()},
        },
    )


# ------------------------------------------------------------------ evaluation


def v1_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Score the v1 heuristic on the SAME rows, by calling the real v1 code.

    Reimplementing the formula here would eventually drift from `minutes.py`;
    building the synthetic element dict v1 expects keeps the comparison honest.
    """
    from fpl_claude.models import minutes as v1

    p_start, p60, exp_minutes = [], [], []
    for r in df.itertuples():
        player = {
            "id": int(r.element),
            "starts": int(r.cum_starts or 0),
            "minutes": int(r.cum_minutes or 0),
            "status": "a",
            "chance_of_playing_next_round": None,
        }
        prior = r.prior_start_share
        est = v1.estimate(
            player,
            int(r.team_games_before or 0),
            None if prior is None or pd.isna(prior) else float(prior),
        )
        p_start.append(est.p_start)
        p60.append(est.p60)
        exp_minutes.append(est.exp_minutes)
    return pd.DataFrame(
        {"p_start": p_start, "p60": p60, "exp_minutes": exp_minutes}, index=df.index
    )


def _log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    """Rank-based AUC (ties averaged) — no sklearn import needed."""
    pos, neg = int(y.sum()), int(len(y) - y.sum())
    if pos == 0 or neg == 0:
        return float("nan")
    order = pd.Series(p).rank(method="average").to_numpy()
    return float((order[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def classification_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "log_loss": round(_log_loss(y, p), 5),
        "brier": round(_brier(y, p), 5),
        "auc": round(_auc(y, p), 5),
        "mean_pred": round(float(np.mean(p)), 5),
        "base_rate": round(float(np.mean(y)), 5),
    }


def regression_metrics(y: np.ndarray, yhat: np.ndarray) -> dict[str, float]:
    err = yhat - y
    return {
        "mae": round(float(np.mean(np.abs(err))), 4),
        "rmse": round(float(np.sqrt(np.mean(err**2))), 4),
        "bias": round(float(np.mean(err)), 4),
    }


def compare(holdout: pd.DataFrame, v2_pred: pd.DataFrame, v1_pred: pd.DataFrame) -> dict[str, Any]:
    y_start = holdout["y_start"].to_numpy()
    y_p60 = holdout["y_p60"].to_numpy()
    y_min = holdout["y_minutes"].to_numpy()
    return {
        "n_rows": len(holdout),
        "p_start": {
            "v1": classification_metrics(y_start, v1_pred["p_start"].to_numpy()),
            "v2": classification_metrics(y_start, v2_pred["p_start"].to_numpy()),
        },
        "p60": {
            "v1": classification_metrics(y_p60, v1_pred["p60"].to_numpy()),
            "v2": classification_metrics(y_p60, v2_pred["p60"].to_numpy()),
        },
        "minutes": {
            "v1": regression_metrics(y_min, v1_pred["exp_minutes"].to_numpy()),
            "v2": regression_metrics(y_min, v2_pred["exp_minutes"].to_numpy()),
        },
    }


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
    """Predicted vs realised by decile of predicted probability."""
    q = pd.qcut(pd.Series(p).rank(method="first"), bins, labels=False)
    rows = []
    for b in range(bins):
        mask = q.to_numpy() == b
        if not mask.any():
            continue
        rows.append(
            {
                "decile": b + 1,
                "n": int(mask.sum()),
                "mean_pred": round(float(p[mask].mean()), 4),
                "actual": round(float(y[mask].mean()), 4),
            }
        )
    return rows


# ------------------------------------------------------------------------- CLI


def _load_split(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = [dataset_for_season(root, s) for s in TRAIN_SEASONS]
    full = pd.concat(frames, ignore_index=True)
    full = full[full["is_cold_start"] == 0].reset_index(drop=True)

    last = TRAIN_SEASONS[-1]
    max_gw = int(full.loc[full["season"] == last, "gw"].max())
    is_valid = (full["season"] == last) & (full["gw"] > max_gw - VALID_TAIL_GWS)
    train_df = full[~is_valid].reset_index(drop=True)
    valid_df = full[is_valid].reset_index(drop=True)

    holdout = dataset_for_season(root, HOLDOUT_SEASON)
    holdout = holdout[holdout["is_cold_start"] == 0].reset_index(drop=True)
    return train_df, valid_df, holdout


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", action="store_true", help="fit and write the artifact")
    parser.add_argument("--data-root", default="db/vaastav")
    parser.add_argument("--out", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--metrics", default="reports/models/minutes-v2-metrics.json")
    args = parser.parse_args(argv)
    if not args.train:
        parser.error("nothing to do — pass --train")

    root = Path(args.data_root)
    print(f"loading {root} …")
    train_df, valid_df, holdout = _load_split(root)
    print(f"train {len(train_df):,}  valid {len(valid_df):,}  holdout {len(holdout):,}")

    model = train(train_df, valid_df)
    out = model.save(args.out)
    print(f"wrote {out}")

    v2_pred = model.predict_frame(holdout)
    v1_pred = v1_baseline(holdout)
    metrics = compare(holdout, v2_pred, v1_pred)
    metrics["meta"] = model.meta
    metrics["holdout_season"] = HOLDOUT_SEASON
    metrics["cameo_minutes"] = model.cameo_minutes
    metrics["calibration_v2_p_start"] = calibration_table(
        holdout["y_start"].to_numpy(), v2_pred["p_start"].to_numpy()
    )
    metrics["calibration_v2_p60"] = calibration_table(
        holdout["y_p60"].to_numpy(), v2_pred["p60"].to_numpy()
    )

    mpath = Path(args.metrics)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("p_start", "p60", "minutes")}, indent=2))
    print(f"wrote {mpath}")


if __name__ == "__main__":
    main()

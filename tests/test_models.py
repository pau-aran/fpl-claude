"""Model layer tests — no network required.

Team-model fitting tests skip cleanly when penaltyblog isn't installed (its
broken `socks` dep on PyPI means it installs via --no-deps; see pyproject).
"""

from __future__ import annotations

import copy
import math

import pandas as pd
import pytest

from fpl_claude.models import minutes as minutes_model
from fpl_claude.models import rates as rates_model
from fpl_claude.models.projections import build_projections, upcoming_gameweeks
from fpl_claude.models.team import fdr_expectation
from fpl_claude.models.xpts import (
    ScoringMap,
    expected_floor_half,
    expected_points,
    poisson_sf,
)
from fpl_claude.rules.engine import Ruleset

# ---------------------------------------------------------------- fixtures


def _player(pid, team, etype, **kw):
    base = {
        "id": pid, "web_name": f"P{pid}", "team": team, "element_type": etype,
        "status": "a", "chance_of_playing_next_round": None, "now_cost": 55,
        "selected_by_percent": "10.0", "minutes": 0, "starts": 0,
        "expected_goals": "0", "expected_assists": "0", "saves": 0,
        "defensive_contribution": 0, "bonus": 0,
    }
    base.update(kw)
    return base


@pytest.fixture
def bootstrap():
    # Two teams, mid-season: 10 team games played each.
    return {
        "teams": [
            {"id": 1, "name": "Arsenal", "short_name": "ARS"},
            {"id": 2, "name": "Spurs", "short_name": "TOT"},
        ],
        "events": [
            {"id": gw, "deadline_time": f"2027-0{2 + gw // 30}-{(gw % 28) + 1:02d}T11:00:00Z",
             "finished": False}
            for gw in range(11, 15)
        ],
        "elements": [
            # Nailed premium mid: 900 mins in 10 starts, strong xG/xA
            _player(10, 1, 3, minutes=900, starts=10, expected_goals="6.0",
                    expected_assists="3.0", bonus=10, now_cost=105,
                    defensive_contribution=40),
            # Nailed keeper
            _player(20, 1, 1, minutes=900, starts=10, saves=30, now_cost=50),
            # Rotation-risk defender: 5 starts of 10, big DC numbers
            _player(30, 1, 2, minutes=450, starts=5, defensive_contribution=60,
                    now_cost=45),
            # Injured forward
            _player(40, 2, 4, status="i", chance_of_playing_next_round=0,
                    minutes=800, starts=9, expected_goals="7.0", now_cost=80),
        ],
    }


@pytest.fixture
def fixtures():
    finished = [
        {"id": i, "event": i, "kickoff_time": f"2026-11-{i:02d}T15:00:00Z",
         "team_h": 1, "team_a": 2, "finished": True,
         "team_h_score": 1, "team_a_score": 1,
         "team_h_difficulty": 3, "team_a_difficulty": 3}
        for i in range(1, 11)
    ]
    upcoming = [
        {"id": 100 + gw, "event": gw, "kickoff_time": f"2027-02-{gw:02d}T15:00:00Z",
         "team_h": 1, "team_a": 2, "finished": False,
         "team_h_difficulty": 2, "team_a_difficulty": 4}
        for gw in range(11, 15)
    ]
    return finished + upcoming


# ---------------------------------------------------------------- minutes


def test_minutes_nailed_starter(bootstrap, fixtures):
    games = minutes_model.team_games_played(fixtures)
    assert games == {1: 10, 2: 10}
    est = minutes_model.estimate(bootstrap["elements"][0], games[1])
    assert est.p_start == 1.0
    assert est.p60 > 0.9
    assert est.confidence == "season"
    assert 70 < est.exp_minutes <= 90


def test_minutes_flagged_player_is_zeroed(bootstrap):
    est = minutes_model.estimate(bootstrap["elements"][3], 10)
    assert est.p_start == 0.0 and est.exp_minutes == 0.0


def test_minutes_preseason_uses_prior_then_neutral():
    player = _player(99, 1, 3)
    with_prior = minutes_model.estimate(player, 0, prior_start_share=0.9)
    assert with_prior.confidence == "prior" and with_prior.p_start == 0.9
    neutral = minutes_model.estimate(player, 0)
    assert neutral.confidence == "neutral" and neutral.p_start == 0.5


def test_minutes_overlay_overrides_with_reason():
    player = _player(99, 1, 3, minutes=900, starts=10)
    est = minutes_model.estimate(
        player, 10, overlay={"start_share": 0.2, "reason": "presser: rotation confirmed"}
    )
    assert est.p_start == pytest.approx(0.2)
    assert est.confidence == "overlay"
    assert est.overlay_reason == "presser: rotation confirmed"


def test_priors_from_previous_season_bootstrap():
    prior_bs = {"elements": [_player(10, 1, 3, starts=38), _player(11, 1, 3, starts=0)]}
    priors = minutes_model.priors_from_bootstrap(prior_bs)
    assert priors == {10: 1.0}  # no-start players yield no prior


# ---------------------------------------------------------------- rates


def test_rates_per90_and_blending(bootstrap):
    current = rates_model.from_bootstrap(bootstrap)
    premium = current.set_index("id").loc[10]
    # Per-90 rates are shrunk toward zero by SHRINKAGE_MINUTES of pseudo-time:
    # 6.0 xG over 900' -> 6.0 * 90 / (900 + 90), not a raw 0.6.
    shrunk = 90.0 / (900 + rates_model.SHRINKAGE_MINUTES)
    assert premium["xg90"] == pytest.approx(6.0 * shrunk)
    assert premium["xa90"] == pytest.approx(3.0 * shrunk)

    # Prior season: same player ran hotter; a 900-min current sample should
    # dominate (weight >= 1 at 6 full matches).
    prior = current.copy()
    prior.loc[prior["id"] == 10, "xg90"] = 1.2
    blended = rates_model.blend(current, prior).set_index("id")
    assert blended.loc[10, "xg90"] == pytest.approx(6.0 * shrunk)

    # Zero-minute player with a prior: takes the prior wholesale.
    zero = _player(50, 1, 4)
    bs2 = {"elements": [zero]}
    cur2 = rates_model.from_bootstrap(bs2)
    prior2 = cur2.copy()
    prior2["xg90"] = 0.5
    blended2 = rates_model.blend(cur2, prior2).set_index("id")
    assert blended2.loc[50, "xg90"] == pytest.approx(0.5)
    assert not blended2.loc[50, "low_sample"]  # has a prior -> not flagged


def test_rates_tiny_sample_does_not_explode():
    # Regression: 1 minute with 0.06 xG must not become a 5.4 xG/90 "player"
    # (2025/26 backtest GW1 captained exactly that artifact pre-shrinkage).
    bs = {"elements": [_player(70, 1, 4, minutes=1, expected_goals="0.06")]}
    rates = rates_model.from_bootstrap(bs).set_index("id")
    assert rates.loc[70, "xg90"] < 0.1


def test_rates_all_zero_prior_column_not_blended():
    # A stat absent from the prior era (dc90 before 2025/26) arrives as an
    # all-zero prior column; blending toward it would strangle real
    # current-season signal (GW1 2025/26 backtest review finding).
    bs = {"elements": [_player(80, 1, 2, minutes=180, defensive_contribution=24,
                               expected_goals="1.0")]}
    current = rates_model.from_bootstrap(bs)
    prior = current.copy()
    prior["dc90"] = 0.0        # field didn't exist last season
    prior["xg90"] = 0.2        # real prior stat: still blends
    blended = rates_model.blend(current, prior).set_index("id")
    assert blended.loc[80, "dc90"] == pytest.approx(current.set_index("id").loc[80, "dc90"])
    assert blended.loc[80, "xg90"] < current.set_index("id").loc[80, "xg90"]


def test_rates_low_sample_flag_without_prior():
    bs = {"elements": [_player(60, 1, 3, minutes=45)]}
    df = rates_model.blend(rates_model.from_bootstrap(bs), None)
    assert bool(df.set_index("id").loc[60, "low_sample"])


def test_shrink_newcomers_regresses_priorless_hot_streak():
    # A priorless newcomer (id 91) with a hot 2-game sample must be regressed
    # toward the position's replacement baseline, not left outranking the
    # established population. Build 6 established MIDs (with a prior) plus the
    # newcomer, all element_type 3.
    established = [
        _player(i, 1, 3, minutes=540, expected_goals=str(0.3 + 0.05 * i))
        for i in range(1, 7)
    ]
    newcomer = _player(91, 2, 3, minutes=180, expected_goals="4.0")  # 2 games, hot
    current = rates_model.from_bootstrap({"elements": established + [newcomer]})
    prior = rates_model.from_bootstrap({"elements": established})  # newcomer absent
    blended = rates_model.blend(current, prior)
    element_type = pd.Series({p["id"]: p["element_type"] for p in established + [newcomer]})
    shrunk = rates_model.shrink_newcomers(blended, element_type).set_index("id")

    raw_new = current.set_index("id").loc[91, "xg90"]
    # Newcomer flagged priorless, evidence = 180/540 = 1/3.
    assert not bool(shrunk.loc[91, "has_prior"])
    assert shrunk.loc[91, "evidence"] == pytest.approx(1 / 3)
    # Regressed strictly below his raw rate...
    assert shrunk.loc[91, "xg90"] < raw_new
    # ...and established players are untouched.
    est_blended = blended.set_index("id").loc[3, "xg90"]
    assert shrunk.loc[3, "xg90"] == pytest.approx(est_blended)
    # The shrink is the evidence-weighted mix toward the position baseline.
    baseline = pd.Series(
        [rates_model.from_bootstrap({"elements": established}).set_index("id").loc[i, "xg90"]
         for i in range(1, 7)]
    ).quantile(rates_model.NEWCOMER_BASELINE_QUANTILE)
    assert shrunk.loc[91, "xg90"] == pytest.approx(raw_new / 3 + baseline * 2 / 3)


# ---------------------------------------------------------------- xpts math


def test_poisson_helpers():
    assert poisson_sf(0, 1.0) == 1.0
    assert poisson_sf(1, 1.0) == pytest.approx(1 - math.exp(-1))
    # E[floor(K/2)] for lam=2: computed independently
    expected = sum((k // 2) * math.exp(-2) * 2**k / math.factorial(k) for k in range(16))
    assert expected_floor_half(2.0) == pytest.approx(expected)


def test_scoring_map_reads_ruleset():
    scoring = ScoringMap.from_ruleset(Ruleset.load("2026-27"))
    assert scoring.goal_points == {"GKP": 10.0, "DEF": 6.0, "MID": 5.0, "FWD": 4.0}
    assert scoring.cs_points["MID"] == 1.0
    assert scoring.dc_rules["DEF"] == {"points": 2, "threshold": 10}


def test_expected_points_components(bootstrap, fixtures):
    """A nailed premium mid at home vs a weak side: sane, decomposed output."""
    scoring = ScoringMap.from_ruleset(Ruleset.load("2026-27"))
    est = minutes_model.estimate(bootstrap["elements"][0], 10)
    rates = rates_model.from_bootstrap(bootstrap).set_index("id").loc[10].to_dict()
    fixture = fdr_expectation(2, 4)  # easy home fixture
    pts = expected_points("MID", rates, est, fixture, is_home=True, scoring=scoring)

    assert pts["appearance"] > 1.8  # nailed -> close to 2
    assert pts["goals"] > 0  # 0.6 xg90 * easy fixture * 5 pts
    assert pts["clean_sheet"] > 0  # MID gets 1 pt CS
    assert pts["conceded"] == 0.0  # MIDs don't lose conceded points
    assert pts["total"] == pytest.approx(
        sum(v for k, v in pts.items() if k != "total"), abs=0.01
    )
    assert 3 < pts["total"] < 12


def test_expected_points_scales_with_rules_yaml(bootstrap):
    """Change the YAML, change the projection — nothing is hard-coded."""
    rules = Ruleset.load("2026-27")
    modified = copy.deepcopy(rules.raw)
    modified["scoring"]["goals"]["MID"] = 10  # double mid goal points
    est = minutes_model.estimate(bootstrap["elements"][0], 10)
    rates = rates_model.from_bootstrap(bootstrap).set_index("id").loc[10].to_dict()
    fixture = fdr_expectation(3, 3)

    base = expected_points("MID", rates, est, fixture, True, ScoringMap.from_ruleset(rules))
    boosted = expected_points(
        "MID", rates, est, fixture, True, ScoringMap.from_ruleset(Ruleset(modified))
    )
    assert boosted["goals"] == pytest.approx(2 * base["goals"], rel=0.01)


def test_positional_enforcement_is_structural(bootstrap):
    """The same (corrupted) rates give position-appropriate points: a keeper
    never earns goal expectation even if the data claims striker-level xG."""
    scoring = ScoringMap.from_ruleset(Ruleset.load("2026-27"))
    fixture = fdr_expectation(3, 3)
    est = minutes_model.estimate(_player(1, 1, 3, minutes=900, starts=10), 10)
    dirty_rates = {"xg90": 0.6, "xa90": 0.3, "saves90": 3.0, "dc90": 13.0, "bonus90": 0.2}

    by_pos = {
        pos: expected_points(pos, dirty_rates, est, fixture, True, scoring)
        for pos in ("GKP", "DEF", "MID", "FWD")
    }
    assert by_pos["GKP"]["goals"] == 0.0  # keepers don't score, whatever the data says
    assert by_pos["DEF"]["goals"] > by_pos["GKP"]["goals"]
    assert by_pos["FWD"]["clean_sheet"] == 0.0  # YAML: FWD CS = 0
    assert by_pos["MID"]["conceded"] == 0.0 and by_pos["FWD"]["conceded"] == 0.0
    assert by_pos["DEF"]["saves"] == 0.0 and by_pos["MID"]["saves"] == 0.0
    assert by_pos["GKP"]["defensive_contribution"] == 0.0  # no GKP DC category
    assert by_pos["DEF"]["defensive_contribution"] > 0.0
    # Same goal involvement is worth more for DEF than FWD (6 vs 4 pts):
    assert by_pos["DEF"]["goals"] > by_pos["FWD"]["goals"]
    # And the totals genuinely differ by position:
    assert len({round(v["total"], 3) for v in by_pos.values()}) == 4

    with pytest.raises(ValueError, match="unknown position"):
        expected_points("WING", dirty_rates, est, fixture, True, scoring)


def test_gk_and_def_specific_components(bootstrap):
    scoring = ScoringMap.from_ruleset(Ruleset.load("2026-27"))
    fixture = fdr_expectation(3, 3)

    gk_est = minutes_model.estimate(bootstrap["elements"][1], 10)
    gk_rates = rates_model.from_bootstrap(bootstrap).set_index("id").loc[20].to_dict()
    gk = expected_points("GKP", gk_rates, gk_est, fixture, True, scoring)
    assert gk["saves"] > 0
    assert gk["conceded"] < 0

    def_est = minutes_model.estimate(bootstrap["elements"][2], 10)
    def_rates = rates_model.from_bootstrap(bootstrap).set_index("id").loc[30].to_dict()
    d = expected_points("DEF", def_rates, def_est, fixture, True, scoring)
    assert d["defensive_contribution"] > 0  # 12 DC/90 vs threshold 10


# ---------------------------------------------------------------- team model


def test_fdr_fallback_shape():
    exp = fdr_expectation(2, 5)
    assert exp.home_xg > exp.away_xg
    assert exp.home_cs_prob == pytest.approx(math.exp(-exp.away_xg), abs=1e-3)
    assert exp.source == "fdr_fallback"


def test_dixon_coles_fit_and_grid_orientation():
    pytest.importorskip("penaltyblog")
    import numpy as np

    from fpl_claude.models.team import TeamModel

    rng = np.random.default_rng(3)
    rows = []
    dates = pd.date_range("2026-08-01", periods=200, freq="D")
    for i in range(100):
        rows.append({"date": dates[2 * i], "home": "Strong", "away": "Weak",
                     "home_goals": int(rng.poisson(2.5)), "away_goals": int(rng.poisson(0.5))})
        rows.append({"date": dates[2 * i + 1], "home": "Weak", "away": "Strong",
                     "home_goals": int(rng.poisson(0.6)), "away_goals": int(rng.poisson(2.1))})
    model = TeamModel.fit(pd.DataFrame(rows))

    exp = model.fixture("Strong", "Weak")
    assert exp.source == "dixon_coles"
    assert exp.home_xg > 1.8 and exp.away_xg < 1.0
    assert exp.home_cs_prob > exp.away_cs_prob
    assert model.covers("Strong", "Weak") and not model.covers("Promoted")


# ---------------------------------------------------------------- pipeline


def test_projections_end_to_end(bootstrap, fixtures):
    df = build_projections(bootstrap, fixtures, horizon=4)
    assert list(df["id"]) == sorted(
        df["id"], key=lambda i: -df.set_index("id").loc[i, "xpts_horizon"]
    )
    table = df.set_index("id")

    # Injured forward projects ~0; nailed premium tops the table.
    assert table.loc[40, "xpts_horizon"] == pytest.approx(0.0, abs=0.1)
    assert df.iloc[0]["id"] == 10
    # Per-GW columns exist for the horizon and decay reduces later weight:
    assert {"xpts_gw11", "xpts_gw14"} <= set(df.columns)
    assert table.loc[10, "xpts_horizon"] < sum(
        table.loc[10, f"xpts_gw{gw}"] for gw in range(11, 15)
    )
    # Value metric present and consistent.
    assert table.loc[10, "xpts_per_m"] == pytest.approx(
        table.loc[10, "xpts_horizon"] / 10.5, rel=0.01
    )
    assert (table["team_model"] == "fdr_fallback").all()


def test_upcoming_gameweeks_respects_horizon(bootstrap):
    assert upcoming_gameweeks(bootstrap, 2) == [11, 12]


def test_overlay_duration_scopes_to_horizon_gws(bootstrap, fixtures):
    """A duration-scoped overlay suppresses only its first N horizon GWs; an
    unscoped overlay covers the whole horizon (safe for ACLs/departures).
    One-week doubts priced as 8-GW absences drove three phantom sells."""
    one_week = {10: {"start_share": 0.0, "reason": "knock: misses next match",
                     "duration_gws": 1}}
    whole = {10: {"start_share": 0.0, "reason": "ACL"}}
    scoped = build_projections(bootstrap, fixtures, overlays=one_week, horizon=4).set_index("id")
    unscoped = build_projections(bootstrap, fixtures, overlays=whole, horizon=4).set_index("id")
    clean = build_projections(bootstrap, fixtures, horizon=4).set_index("id")

    assert scoped.loc[10, "xpts_gw11"] < 1.0  # overlaid week: near-zero
    # Beyond duration the clean estimate returns:
    assert scoped.loc[10, "xpts_gw12"] == pytest.approx(clean.loc[10, "xpts_gw12"], rel=0.01)
    # Unscoped stays suppressed across the horizon:
    assert unscoped.loc[10, "xpts_gw12"] < 1.0
    assert scoped.loc[10, "xpts_horizon"] > unscoped.loc[10, "xpts_horizon"]

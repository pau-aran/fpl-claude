"""Minutes v2 tests — fully offline, synthetic frames only.

Two things are being defended here, and they are the two things that would hurt
most if they broke silently:

  1. **No leakage.** Every history feature for GW n must be computable from GWs
     strictly before n. The test does not inspect the implementation; it mutates
     the future and asserts the past does not move, which is the only version of
     this check that survives a refactor.
  2. **Precedence and graceful degradation.** With no artifact the pipeline must
     be v1 to the digit, and with one the overlay must still win. A minutes model
     that quietly overrode a written press-conference read would violate
     CLAUDE.md rule 4 and nothing downstream would notice.

Nothing here touches the network or the shared `db/` archive: the frames are
hand-built and the "boosters" are constant stubs, so the file runs in
milliseconds on a fresh clone with no lightgbm installed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fpl_claude.models import minutes as v1
from fpl_claude.models import minutes_v2 as m2

TEAMS = [(1, "Arsenal"), (2, "Spurs")]
N_GW = 8

# Player 1 nailed, 2 rotating, 3 fringe (all Arsenal); 4 nailed for Spurs;
# 5 is a debutant with no history and no prior season (the cold-start case).
PLAYER_MINUTES = {
    1: [90, 90, 90, 90, 90, 90, 90, 90],
    2: [90, 0, 20, 90, 0, 75, 0, 90],
    3: [0, 0, 12, 0, 0, 0, 8, 0],
    4: [88, 90, 90, 0, 90, 90, 90, 62],
    5: [0, 0, 0, 0, 0, 0, 0, 0],
}
PLAYER_STARTS = {
    pid: [1 if m >= 60 else 0 for m in mins] for pid, mins in PLAYER_MINUTES.items()
}
PLAYER_TEAM = {1: 1, 2: 1, 3: 1, 4: 2, 5: 1}
PLAYER_POS = {1: "MID", 2: "DEF", 3: "FWD", 4: "GK", 5: "MID"}


def _kickoff(gw: int) -> str:
    """Weekly Saturday 15:00 kickoffs, so rest days read a clean 7 throughout."""
    return (pd.Timestamp("2026-08-15T14:00:00Z") + pd.Timedelta(days=7 * (gw - 1))).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _frames() -> dict[str, pd.DataFrame]:
    fixtures = pd.DataFrame(
        [
            {
                "id": gw, "event": gw, "team_h": 1 if gw % 2 else 2,
                "team_a": 2 if gw % 2 else 1, "team_h_difficulty": 3,
                "team_a_difficulty": 4, "kickoff_time": _kickoff(gw),
                "team_h_score": 1, "team_a_score": 0, "finished": True,
            }
            for gw in range(1, N_GW + 1)
        ]
    )
    home_team = fixtures.set_index("event")["team_h"].to_dict()
    rows = []
    for pid, mins in PLAYER_MINUTES.items():
        for gw, minute in enumerate(mins, start=1):
            rows.append(
                {
                    "element": pid, "GW": gw, "fixture": gw, "minutes": minute,
                    "starts": PLAYER_STARTS[pid][gw - 1], "value": 50 + 5 * pid,
                    "selected": 1000 * pid, "was_home": PLAYER_TEAM[pid] == home_team[gw],
                    "opponent_team": 3 - PLAYER_TEAM[pid], "kickoff_time": _kickoff(gw),
                    "position": PLAYER_POS[pid], "team": dict(TEAMS)[PLAYER_TEAM[pid]],
                }
            )
    teams = pd.DataFrame([{"id": t, "name": n} for t, n in TEAMS])
    players = pd.DataFrame([{"id": pid, "code": 1000 + pid} for pid in PLAYER_MINUTES])
    # Player 5 has no prior-season row at all — the cold start.
    prior_players = pd.DataFrame(
        [
            {"id": pid, "code": 1000 + pid, "minutes": 2000, "starts": 25}
            for pid in (1, 2, 3, 4)
        ]
    )
    return {
        "merged": pd.DataFrame(rows),
        "fixtures": fixtures,
        "teams": teams,
        "players": players,
        "prior_players": prior_players,
        "prior_fixtures": fixtures,
        "prior_teams": teams,
    }


def _build(frames: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    f = frames or _frames()
    return m2.build_features(season="2026-27", **f)


@pytest.fixture
def features() -> pd.DataFrame:
    return _build()


# ------------------------------------------------------------ feature builder


def test_rolling_history_matches_hand_computation(features):
    """start_share_3 / mins_last must be the previous gameweeks, nothing else."""
    p2 = features[features.element == 2].set_index("GW").sort_index()
    # Player 2's starts by GW: 1,0,0,1,0,1,0,1 (minutes >= 60 == started).
    assert p2.loc[1, "start_share_3"] != p2.loc[1, "start_share_3"]  # NaN at GW1
    assert p2.loc[2, "start_share_3"] == pytest.approx(1.0)  # GW1 only
    assert p2.loc[4, "start_share_3"] == pytest.approx(1 / 3)  # GW1-3: 1,0,0
    assert p2.loc[5, "start_share_3"] == pytest.approx(1 / 3)  # GW2-4: 0,0,1
    assert p2.loc[6, "mins_last"] == pytest.approx(0.0)  # GW5 minutes
    assert p2.loc[7, "mins_last"] == pytest.approx(75.0)  # GW6 minutes


def test_streaks_count_only_prior_gameweeks(features):
    p1 = features[features.element == 1].set_index("GW").sort_index()
    assert p1.loc[1, "starts_streak"] == 0  # nothing behind him yet
    assert p1.loc[4, "starts_streak"] == 3  # started GW1-3
    p3 = features[features.element == 3].set_index("GW").sort_index()
    assert p3.loc[5, "benched_streak"] == 4


def test_targets_are_not_features(features):
    """The outcome columns must never appear in the model matrix."""
    assert not set(m2.TARGETS) & set(m2.FEATURES)
    assert set(m2.FEATURES).issubset(features.columns)


def test_cold_start_is_flagged_and_never_predicted(features):
    """Player 5 debuts with no prior season: v2 must decline, not guess."""
    p5_gw1 = features[(features.element == 5) & (features.GW == 1)].iloc[0]
    assert p5_gw1.is_cold_start == 1
    p1_gw1 = features[(features.element == 1) & (features.GW == 1)].iloc[0]
    assert p1_gw1.is_cold_start == 0  # has a prior-season record


def test_congestion_and_calendar_features_are_sane(features):
    """Fixtures are a week apart here, so rest days must read 7 throughout."""
    later = features[features.GW > 1]
    assert (later.days_since_prev == 7).all()
    assert (features[features.GW < N_GW].days_to_next == 7).all()
    assert (features.team_fix_last_7 <= 1).all()
    assert set(features.is_midweek.unique()) <= {0, 1}
    assert (features.team_fixtures_this_gw == 1).all()


def test_afcon_and_uefa_masks_follow_the_calendar():
    kickoffs = pd.Series(pd.to_datetime(["2024-01-20T15:00:00Z", "2024-03-02T15:00:00Z"]))
    afcon = m2._afcon_mask(kickoffs, "2023-24")
    assert afcon.tolist() == [1, 0]
    assert m2._afcon_mask(kickoffs, "2024-25").tolist() == [0, 0]  # no AFCON that season
    uefa = m2._uefa_mask(
        pd.Series(pd.to_datetime(["2023-08-15T15:00:00Z", "2023-10-21T15:00:00Z"])), "2023-24"
    )
    assert uefa.tolist() == [0, 1]  # Europe is dark in August


# ------------------------------------------------------------------- leakage


def test_features_for_gw_n_use_only_gameweeks_before_n():
    """Rewrite the future; the past must not move by a single float.

    This is the test that matters. It makes no assumption about how the rolling
    windows are implemented — it asserts the property directly, so a future
    refactor that reaches forward gets caught even if it looks correct.
    """
    cutoff = 5
    base = _build()

    tampered = _frames()
    m = tampered["merged"]
    future = m["GW"] >= cutoff
    m.loc[future, "minutes"] = 90 - m.loc[future, "minutes"]
    m.loc[future, "starts"] = 1 - m.loc[future, "starts"]
    m.loc[future, "value"] = 999
    m.loc[future, "selected"] = 123_456
    after = _build(tampered)

    key = ["element", "GW"]
    cols = key + list(m2.FEATURES)
    a = base[base.GW < cutoff].sort_values(key)[cols].reset_index(drop=True)
    b = after[after.GW < cutoff].sort_values(key)[cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_slicing_one_gameweek_equals_building_only_the_past():
    """Predicting GW n from the full-season frame must equal building the frame
    from truncated history — otherwise a live run and a replay disagree."""
    cutoff = 6
    full = _build()
    frames = _frames()
    frames["merged"] = frames["merged"][frames["merged"]["GW"] <= cutoff]
    truncated = m2.build_features(season="2026-27", **frames)

    key = ["element", "GW"]
    cols = key + [f for f in m2.FEATURES if f not in ("days_to_next",)]
    a = full[full.GW == cutoff].sort_values(key)[cols].reset_index(drop=True)
    b = truncated[truncated.GW == cutoff].sort_values(key)[cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


# ------------------------------------------------------- model plumbing (stub)


class _StubBooster:
    """Stands in for a LightGBM Booster so the tests need no lightgbm."""

    def __init__(self, value: float):
        self.value = value

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.value, dtype=float)


def _stub_model(p_start=0.7, p_play=0.4, p60=0.9, mins=120.0) -> m2.MinutesModelV2:
    """Deliberately incoherent and out of range: p60 > p_play, minutes > 90."""
    return m2.MinutesModelV2(
        boosters={
            "p_start": _StubBooster(p_start),
            "p_play": _StubBooster(p_play),
            "p60": _StubBooster(p60),
            "mins_given_start": _StubBooster(mins),
        },
        cameo_minutes=18.0,
    )


def test_predictions_are_coherent_and_in_range(features):
    out = _stub_model().predict_frame(features)
    probs = out[["p_start", "p_play", "p60", "p_cameo"]]
    assert ((probs >= 0.0) & (probs <= 1.0)).all().all()
    assert out.exp_minutes.between(0.0, 90.0).all()
    assert (out.p60 <= out.p_play + 1e-9).all()
    assert (out.p_start <= out.p_play + 1e-9).all()
    assert (out.p_cameo >= 0.0).all()
    assert out.mins_given_start.between(1.0, 90.0).all()


def test_predict_gw_skips_cold_starts(features):
    gw1 = features[features.GW == 1]
    preds = _stub_model().predict_gw(gw1)
    assert 5 not in preds  # the debutant
    assert set(preds) == {1, 2, 3, 4}
    est = preds[1]
    assert 0.0 <= est.start_share <= 1.0
    assert 0.0 <= est.p60_given_start <= 1.0
    assert 0.0 <= est.minutes_given_start <= 90.0


def test_load_model_returns_none_when_artifact_missing(tmp_path):
    assert m2.load_model(tmp_path / "nope.joblib") is None


def test_load_model_returns_none_on_a_corrupt_artifact(tmp_path):
    bad = tmp_path / "minutes_v2.joblib"
    bad.write_bytes(b"not a joblib file")
    assert m2.load_model(bad) is None


# ------------------------------------------------ precedence and v1 fallback


def _bootstrap() -> dict:
    return {
        "elements": [
            {
                "id": 1, "team": 1, "element_type": 3, "status": "a",
                "chance_of_playing_next_round": None, "starts": 8, "minutes": 700,
            },
            {
                "id": 2, "team": 1, "element_type": 2, "status": "a",
                "chance_of_playing_next_round": None, "starts": 4, "minutes": 300,
            },
        ]
    }


def test_no_model_is_byte_identical_to_v1():
    """The default path must not move — the 2025-26 backtest depends on it."""
    boot, games = _bootstrap(), {1: 10}
    plain = v1.estimate_all(boot, games)
    with_none = v1.estimate_all(boot, games, model=None)
    with_empty = v1.estimate_all(boot, games, model={})
    pd.testing.assert_frame_equal(plain, with_none)
    pd.testing.assert_frame_equal(plain, with_empty)
    # And the actual v1 arithmetic, locked: 8 starts / 10 games, 700/8 min per start.
    row = plain.set_index("id").loc[1]
    assert row.p_start == pytest.approx(0.8)
    assert row.p_cameo == pytest.approx(0.06)
    # 700/8 = 87.5 min per start, so p60|start saturates at v1's 0.98 ceiling.
    assert row.p60 == pytest.approx(0.8 * 0.98, abs=1e-4)
    assert row.exp_minutes == pytest.approx(0.8 * 78 + 0.06 * 18, abs=0.01)


def test_model_supersedes_the_heuristic():
    model = {
        1: v1.ModelMinutes(
            start_share=0.35, cameo_share=0.25, p60_given_start=0.6,
            minutes_given_start=70.0, cameo_minutes=20.0,
        )
    }
    row = v1.estimate_all(_bootstrap(), {1: 10}, model=model).set_index("id").loc[1]
    assert row.p_start == pytest.approx(0.35)
    assert row.p_cameo == pytest.approx(0.25)
    assert row.p60 == pytest.approx(0.35 * 0.6)
    assert row.exp_minutes == pytest.approx(0.35 * 70 + 0.25 * 20, abs=0.01)
    assert row.minutes_confidence == "model"
    # Player 2 has no model entry: he stays on the heuristic.
    other = v1.estimate_all(_bootstrap(), {1: 10}, model=model).set_index("id").loc[2]
    assert other.minutes_confidence == "season"
    assert other.p_start == pytest.approx(0.4)


def test_overlay_still_beats_the_model():
    """CLAUDE.md rule 4: a written team-news read outranks any number."""
    model = {
        1: v1.ModelMinutes(
            start_share=0.95, cameo_share=0.02, p60_given_start=0.9,
            minutes_given_start=88.0,
        )
    }
    overlays = {1: {"start_share": 0.0, "reason": "hamstring, ruled out in presser"}}
    row = (
        v1.estimate_all(_bootstrap(), {1: 10}, overlays=overlays, model=model)
        .set_index("id")
        .loc[1]
    )
    assert row.p_start == pytest.approx(0.0)
    assert row.p60 == pytest.approx(0.0)
    assert row.minutes_confidence == "overlay"
    assert row.overlay_reason == "hamstring, ruled out in presser"


def test_availability_flag_still_gates_the_model():
    """No archive we train on has injury flags, so the flag stays a multiplier
    applied on top of the model rather than something the model can override."""
    boot = _bootstrap()
    boot["elements"][0]["status"] = "i"
    model = {
        1: v1.ModelMinutes(
            start_share=0.95, cameo_share=0.02, p60_given_start=0.9,
            minutes_given_start=88.0,
        )
    }
    row = v1.estimate_all(boot, {1: 10}, model=model).set_index("id").loc[1]
    assert row.p_start == pytest.approx(0.0)
    assert row.exp_minutes == pytest.approx(0.0)


def test_model_output_is_clamped_before_it_reaches_the_estimate():
    """A model handing back nonsense must not produce a nonsense estimate."""
    model = {
        1: v1.ModelMinutes(
            start_share=1.7, cameo_share=0.9, p60_given_start=2.0,
            minutes_given_start=140.0, cameo_minutes=-5.0,
        )
    }
    row = v1.estimate_all(_bootstrap(), {1: 10}, model=model).set_index("id").loc[1]
    assert 0.0 <= row.p_start <= 1.0
    assert 0.0 <= row.p_cameo <= 1.0
    assert 0.0 <= row.p60 <= 1.0
    assert 0.0 <= row.exp_minutes <= 90.0

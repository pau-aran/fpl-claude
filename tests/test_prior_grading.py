"""Prior grading: a prior ROW is not a prior SAMPLE.

Covers the four defects found on the first live 2026/27 projections run
(research/2026-27/projections-run.md) — zeroed priors read as measured zeros,
thin priors read as confident, priors carried across a club change, and a team
model trusting stale results. Each test names the player the defect was found
on, so a regression says what it broke.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fpl_claude.data import football_data
from fpl_claude.models import minutes as minutes_model
from fpl_claude.models import rates as rates_model
from fpl_claude.models.team import MIN_RECENT_MATCHES, MIN_TEAM_MATCHES, TeamModel


def _rates_frame(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    """(id, minutes_sample, xg90) -> a rates-shaped frame."""
    return pd.DataFrame(
        [
            {
                "id": pid,
                "minutes_sample": mins,
                "xg90": xg,
                "xa90": 0.1,
                "saves90": 0.0,
                "dc90": 1.0,
                "bonus90": 0.1,
            }
            for pid, mins, xg in rows
        ]
    )


# --------------------------------------------------------------- rates: D3/D2


def test_zero_minute_prior_is_not_evidence():
    """D3 — Rashford: a prior row of zeros from a loan spell was weighted 1.0
    pre-season, so he carried a MEASURED xg90 of 0.00 at £7.0m."""
    current = _rates_frame([(1, 0, 0.0)])
    prior = _rates_frame([(1, 0, 0.0)])  # row exists, no minutes behind it
    out = rates_model.blend(current, prior).set_index("id")
    assert out.loc[1, "prior_strength"] == 0.0
    assert not out.loc[1, "has_prior"], "a zeroed row must not count as a prior"
    assert out.loc[1, "evidence"] == 0.0
    assert out.loc[1, "low_sample"]


def test_thin_prior_is_partial_evidence_and_flagged():
    """D2 — Isak: 694 minutes around a fibula fracture presented with the same
    confidence as a 3000-minute season."""
    current = _rates_frame([(1, 0, 0.0)])
    prior = _rates_frame([(1, 694, 0.8)])
    out = rates_model.blend(current, prior).set_index("id")
    assert 0.0 < out.loc[1, "prior_strength"] < 1.0
    assert out.loc[1, "low_sample"], "thin evidence must be visible in the table"
    assert out.loc[1, "evidence"] == pytest.approx(694 / rates_model.PRIOR_FULL_WEIGHT_MINUTES)


def test_full_prior_is_unchanged_regression_guard():
    """The gate result (2025/26 GW1-10, 624 v 531) rests on established players.
    At full prior strength this must be arithmetically what it always was."""
    current = _rates_frame([(1, 0, 0.0)])
    prior = _rates_frame([(1, 3000, 0.55)])
    out = rates_model.blend(current, prior).set_index("id")
    assert out.loc[1, "prior_strength"] == 1.0
    assert out.loc[1, "evidence"] == 1.0
    assert not out.loc[1, "low_sample"]
    assert out.loc[1, "xg90"] == pytest.approx(0.55)


def test_thin_prior_is_regressed_toward_replacement_not_left_alone():
    """The shortfall in evidence is spent on the positional baseline, so a thin
    prior lands between its own rate and replacement level."""
    established = [(i, 3000, 0.5 + i * 0.01) for i in range(2, 12)]
    current = _rates_frame([(1, 0, 0.0), *[(i, 0, 0.0) for i, _, _ in established]])
    prior = _rates_frame([(1, 200, 2.0), *established])  # a wild 200-minute rate
    blended = rates_model.blend(current, prior)
    element_type = pd.Series({i: 4 for i in blended["id"]})
    out = rates_model.shrink_newcomers(blended, element_type).set_index("id")
    assert out.loc[1, "xg90"] < 2.0, "a 200-minute rate must not survive intact"
    assert out.loc[2, "xg90"] == pytest.approx(0.52), "established players untouched"


# ------------------------------------------------------------- minutes: D2/D4


def _player(pid: int = 1, starts: int = 0, minutes: int = 0) -> dict:
    return {"id": pid, "starts": starts, "minutes": minutes, "status": "a"}


def test_prior_from_a_different_club_is_discounted():
    """D4 — Dubravka: 35 Newcastle starts made a 37-year-old third-choice Spurs
    keeper the highest xPts/£m player in the entire game."""
    prior = minutes_model.StartSharePrior(share=0.92, minutes=3150, team_code=90)
    est = minutes_model.estimate(_player(), team_games=0, prior_start_share=prior,
                                 current_team_code=6)
    assert est.confidence == "prior_new_club"
    assert est.p_start < 0.92, "a move must cost the prior some weight"
    assert est.p_start > minutes_model.NEUTRAL_START_SHARE, "but a starter is still a starter"


def test_same_club_full_prior_is_trusted_in_full():
    prior = minutes_model.StartSharePrior(share=0.92, minutes=3150, team_code=6)
    est = minutes_model.estimate(_player(), team_games=0, prior_start_share=prior,
                                 current_team_code=6)
    assert est.confidence == "prior"
    assert est.p_start == pytest.approx(0.92)


def test_thin_minutes_prior_is_regressed_toward_neutral():
    """A start share resting on few minutes cannot tell 'benched' from
    'injured', so it is not believed at face value."""
    prior = minutes_model.StartSharePrior(share=0.21, minutes=694, team_code=14)
    est = minutes_model.estimate(_player(), team_games=0, prior_start_share=prior,
                                 current_team_code=14)
    assert est.confidence == "prior_thin"
    assert est.p_start > 0.21, "regressed up toward neutral, not left at 0.21"
    assert est.p_start < minutes_model.NEUTRAL_START_SHARE


def test_bare_float_prior_still_supported():
    """Older callers pass a plain share; it is trusted as before."""
    est = minutes_model.estimate(_player(), team_games=0, prior_start_share=0.8)
    assert est.confidence == "prior"
    assert est.p_start == pytest.approx(0.8)


# ------------------------------------------------------------------- team: D6


def _model_with(counts: dict[str, int], recent: dict[str, int]) -> TeamModel:
    return TeamModel(model=None, teams=set(counts), match_counts=counts, recent_counts=recent)


def test_stale_history_does_not_earn_a_rating():
    """D6 — Ipswich: relegated, promoted again, carrying 38 matches that are all
    from the relegation season. Only a name mismatch hid it."""
    m = _model_with({"Ipswich Town": 38}, {"Ipswich Town": 0})
    assert not m.covers("Ipswich Town")


def test_recent_history_earns_a_rating():
    m = _model_with(
        {"Sunderland": MIN_TEAM_MATCHES}, {"Sunderland": MIN_RECENT_MATCHES}
    )
    assert m.covers("Sunderland")


def test_recent_counts_default_to_match_counts():
    """Hand-built models (tests, callers without recency data) behave as before."""
    m = TeamModel(model=None, teams={"Arsenal"}, match_counts={"Arsenal": 40})
    assert m.covers("Arsenal")


def test_promoted_club_names_map_to_fpl_names():
    """The mapping is silent on failure — an unmapped club just quietly loses
    its whole history, which is how Ipswich broke."""
    for football_data_name in ("Ipswich", "Hull", "Coventry"):
        assert football_data_name in football_data.TO_FPL_NAME
    # FPL uses the bare forms for these; "helpfully" expanding them zeroed
    # Leeds' entire history on the first attempt at this fix.
    assert "Leeds" not in football_data.TO_FPL_NAME
    assert "Newcastle" not in football_data.TO_FPL_NAME

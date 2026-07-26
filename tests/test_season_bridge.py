"""Cross-season bridge tests — no network required.

The failure this module exists to prevent is SILENT: joining last season's
element ids to this season's produces a full, plausible-looking table in which
every player carries someone else's history. So the tests assert on identity
(did player X get player X's numbers?), not just on shapes.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from fpl_claude.data.season_bridge import (
    coverage,
    prior_bootstrap_from_vaastav,
)
from fpl_claude.models import minutes as minutes_model
from fpl_claude.models import rates as rates_model

# ---------------------------------------------------------------- fixtures


@pytest.fixture
def current_bootstrap():
    """This season: ids 1-4. Codes are the stable key.

    - code 100 (Established): kept his club, id changed 7 -> 1
    - code 200 (Mover):       new club, id changed 3 -> 2
    - code 300 (Newcomer):    no prior row at all (summer signing)
    - code 400 (Promoted):    no prior row (promoted-club player)
    """
    return {
        "teams": [
            {"id": 1, "name": "Arsenal"},
            {"id": 2, "name": "Hull City"},
        ],
        "elements": [
            {"id": 1, "code": 100, "team": 1, "element_type": 3, "web_name": "Established"},
            {"id": 2, "code": 200, "team": 1, "element_type": 4, "web_name": "Mover"},
            {"id": 3, "code": 300, "team": 1, "element_type": 2, "web_name": "Newcomer"},
            {"id": 4, "code": 400, "team": 2, "element_type": 1, "web_name": "Promoted"},
        ],
    }


@pytest.fixture
def prior_csv(tmp_path):
    """Last season's players_raw.csv: DIFFERENT ids for the same codes, plus a
    player (code 900) who has since left the league."""
    df = pd.DataFrame(
        [
            {"code": 100, "id": 7, "web_name": "Established", "element_type": 3,
             "minutes": 2700, "starts": 30, "expected_goals": 12.5,
             "expected_assists": 8.0, "saves": 0, "defensive_contribution": 250,
             "bonus": 20},
            {"code": 200, "id": 3, "web_name": "Mover", "element_type": 4,
             "minutes": 1800, "starts": 20, "expected_goals": 9.0,
             "expected_assists": 2.0, "saves": 0, "defensive_contribution": 100,
             "bonus": 11},
            {"code": 900, "id": 1, "web_name": "Departed", "element_type": 3,
             "minutes": 3200, "starts": 38, "expected_goals": 0.5,
             "expected_assists": 0.5, "saves": 0, "defensive_contribution": 400,
             "bonus": 2},
        ]
    )
    path = tmp_path / "players_raw.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    return path


# ---------------------------------------------------------------- remapping


def test_remaps_ids_by_code_not_by_id(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    by_id = {e["id"]: e for e in prior["elements"]}

    # Established: prior id 7 -> current id 1, carrying HIS numbers.
    assert by_id[1]["code"] == 100
    assert by_id[1]["minutes"] == 2700
    assert by_id[1]["expected_goals"] == pytest.approx(12.5)
    # Mover: prior id 3 -> current id 2.
    assert by_id[2]["code"] == 200
    assert by_id[2]["starts"] == 20


def test_naive_id_join_would_have_been_wrong(current_bootstrap, prior_csv):
    """Guard on the actual bug: a raw id-join would give current id 1 the
    numbers of prior id 1 ("Departed"), not his own."""
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    by_id = {e["id"]: e for e in prior["elements"]}
    departed_minutes = 3200
    assert by_id[1]["minutes"] != departed_minutes


def test_priorless_players_are_dropped_not_zero_filled(current_bootstrap, prior_csv):
    """A zeroed prior reads as 'played and was bad'; absence reads as unknown,
    which is what the shrink_newcomers machinery is built for."""
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    ids = {e["id"] for e in prior["elements"]}
    assert 3 not in ids  # Newcomer
    assert 4 not in ids  # Promoted-club player


def test_departed_players_are_dropped(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    assert 900 not in {e["code"] for e in prior["elements"]}


def test_carries_every_field_the_model_layers_read(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    consumed = {
        "id", "minutes", "starts", "expected_goals", "expected_assists",
        "saves", "defensive_contribution", "bonus", "element_type",
    }
    for element in prior["elements"]:
        assert consumed.issubset(element.keys())


def test_missing_column_becomes_zero_not_nan(current_bootstrap, tmp_path):
    """Pre-2025/26 seasons have no `defensive_contribution` column; NaN would
    poison every per-90 downstream."""
    df = pd.DataFrame(
        [{"code": 100, "id": 7, "web_name": "E", "element_type": 3, "minutes": 900,
          "starts": 10, "expected_goals": 4.0, "expected_assists": 1.0,
          "saves": 0, "bonus": 5}]
    )
    path = tmp_path / "old.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    prior = prior_bootstrap_from_vaastav(current_bootstrap, path)
    element = prior["elements"][0]
    assert element["defensive_contribution"] == 0
    rates = rates_model.from_bootstrap(prior)
    assert rates.notna().all().all()


def test_min_minutes_routes_thin_priors_to_the_priorless_path(current_bootstrap, prior_csv):
    """A row of near-zeros (injured / out on loan all season) is ABSENCE, not a
    measurement of zero. With the threshold on, such a player must vanish from
    the prior so `shrink_newcomers` treats him as an unknown."""
    default = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    assert {e["id"] for e in default["elements"]} == {1, 2}  # Mover has 1800 mins

    thinned = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv, min_minutes=2000)
    assert {e["id"] for e in thinned["elements"]} == {1}  # only the 2700-min player

    blended = rates_model.blend(
        rates_model.from_bootstrap(
            {"elements": [
                {"id": e["id"], "minutes": 0, "expected_goals": 0, "expected_assists": 0,
                 "saves": 0, "defensive_contribution": 0, "bonus": 0}
                for e in current_bootstrap["elements"]
            ]}
        ),
        rates_model.from_bootstrap(thinned),
    ).set_index("id")
    assert bool(blended.loc[2, "has_prior"]) is False


def test_rejects_a_csv_without_code(current_bootstrap, tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame([{"id": 7, "element_type": 3, "minutes": 90, "starts": 1}]).to_csv(
        path, index=False, encoding="utf-8"
    )
    with pytest.raises(ValueError, match="code"):
        prior_bootstrap_from_vaastav(current_bootstrap, path)


# ---------------------------------------------------------------- consumers


def test_output_feeds_the_minutes_and_rates_layers(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)

    priors = minutes_model.priors_from_bootstrap(prior)
    # The prior is a StartSharePrior, not a bare float: the share travels with
    # the minutes behind it and the club it was earned at, so the minutes layer
    # can discount a thin sample or a move without re-deriving either.
    assert priors[1].share == pytest.approx(30 / 38)  # current id, prior starts
    assert priors[1].minutes == 2700
    assert 3 not in priors and 4 not in priors

    blended = rates_model.blend(
        rates_model.from_bootstrap(
            {"elements": [
                {"id": e["id"], "minutes": 0, "expected_goals": 0, "expected_assists": 0,
                 "saves": 0, "defensive_contribution": 0, "bonus": 0}
                for e in current_bootstrap["elements"]
            ]}
        ),
        rates_model.from_bootstrap(prior),
    ).set_index("id")
    assert bool(blended.loc[1, "has_prior"]) is True
    assert bool(blended.loc[3, "has_prior"]) is False
    assert bool(blended.loc[3, "low_sample"]) is True
    # Pre-season the current sample is zero, so a player WITH a prior projects
    # entirely off that prior rather than off nothing.
    assert blended.loc[1, "xg90"] > 0


# ---------------------------------------------------------------- coverage


def test_coverage_breaks_down_by_position_and_club(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    cov = coverage(current_bootstrap, prior)

    assert (cov.matched_players, cov.total_players) == (2, 4)
    assert cov.pct == pytest.approx(50.0)
    assert cov.by_position["MID"] == (1, 1)
    assert cov.by_position["DEF"] == (0, 1)
    assert cov.by_team["Arsenal"] == (2, 3)
    # Promoted club: near-empty is the CORRECT answer, and a high number here
    # would mean the join is matching the wrong thing.
    assert cov.by_team["Hull City"] == (0, 1)
    assert "Hull City" in cov.to_text()


def test_coverage_text_is_ascii_safe(current_bootstrap, prior_csv):
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    coverage(current_bootstrap, prior).to_text().encode("cp1252")


def test_payload_is_json_serializable(current_bootstrap, prior_csv):
    """The CLI writes it to disk; numpy ints from pandas would blow up here."""
    prior = prior_bootstrap_from_vaastav(current_bootstrap, prior_csv)
    assert json.loads(json.dumps(prior))["elements"][0]["id"] == 1

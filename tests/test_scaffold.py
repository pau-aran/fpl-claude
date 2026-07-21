"""Scaffold sanity tests — no network required."""

import json
from pathlib import Path

from fpl_claude.rules.engine import Ruleset
from fpl_claude.reports import team_week


def test_ruleset_loads_and_reports_unverified():
    rules = Ruleset.load("2026-27")
    assert rules.season == "2026-27"
    assert not rules.is_verified()  # must stay false until season-launch verification
    assert "chips" in rules.unverified_sections()
    assert rules.squad_shape() == {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    assert rules.policy("hit_ev_threshold") == 4.5


def test_team_week_report_from_fixture_data(tmp_path: Path):
    """Report builder works offline from a snapshot directory."""
    day = tmp_path / "raw" / "2026-07-21"
    day.mkdir(parents=True)
    bootstrap = {
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS"}],
        "elements": [
            {
                "id": 10, "web_name": "Saka", "team": 1, "element_type": 3,
                "status": "d", "news": "Knock - 75% chance of playing",
                "chance_of_playing_next_round": 75, "selected_by_percent": "45.3",
            }
        ],
        "events": [],
    }
    (day / "bootstrap.json").write_text(json.dumps(bootstrap))
    (day / "fixtures.json").write_text(json.dumps([]))

    original_raw = team_week.RAW_DIR
    team_week.RAW_DIR = tmp_path / "raw"
    try:
        out = team_week.build_reports(from_snapshot="2026-07-21", out_dir=tmp_path / "out")
    finally:
        team_week.RAW_DIR = original_raw

    report = (out / "arsenal.md").read_text()
    assert "Saka" in report and "DOUBTFUL" in report and "75% next round" in report
    assert (out / "index.md").exists()

"""Scaffold sanity tests — no network required."""

import copy
import json
from pathlib import Path

import pytest

from fpl_claude.reports import team_week
from fpl_claude.rules.engine import Ruleset


def test_ruleset_loads_and_is_verified():
    """2026/27 was verified against the live game on 2026-07-25 (see
    research/2026-27/rules-verification.md). Every section must stay verified;
    if FPL changes a rule mid-season, re-verify rather than relaxing this test."""
    rules = Ruleset.load("2026-27")
    assert rules.season == "2026-27"
    assert rules.is_verified()
    assert rules.unverified_sections() == []
    assert rules.squad_shape() == {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    assert rules.policy("hit_ev_threshold") == 4.5


def test_ruleset_verification_gate_still_detects_unverified_sections():
    """The gate itself must keep working — a section flagged for verification
    makes the whole ruleset unverified, which is what blocks the optimizer."""
    rules = Ruleset.load("2026-27")
    raw = copy.deepcopy(rules.raw)
    raw["chips"]["verify_at_season_launch"] = True
    stale = Ruleset(raw)
    assert stale.unverified_sections() == ["chips"]
    assert not stale.is_verified()


def test_verified_2026_27_matches_the_api_snapshot():
    """Machine-truth cross-check: the fields FPL publishes in bootstrap.json must
    agree with the YAML, so a silent mid-season rule change gets caught."""
    snapshot = Path(__file__).resolve().parents[1] / "db" / "raw" / "2026-07-25" / "bootstrap.json"
    if not snapshot.exists():  # snapshots are append-only but not guaranteed in CI
        pytest.skip("2026-07-25 snapshot not present")
    boot = json.loads(snapshot.read_text(encoding="utf-8"))
    settings, scoring = boot["game_settings"], boot["game_config"]["scoring"]
    rules = Ruleset.load("2026-27")

    assert rules.raw["squad"]["size"] == settings["squad_squadsize"]
    assert rules.raw["squad"]["max_per_club"] == settings["squad_team_limit"]
    assert rules.raw["lineup"]["starting"] == settings["squad_squadplay"]
    assert rules.raw["budget"]["initial"] * settings["ui_currency_multiplier"] == (
        settings["squad_total_spend"]
    )
    # 1 base free transfer + max_extra_free_transfers banked
    assert rules.raw["transfers"]["max_banked"] == settings["max_extra_free_transfers"] + 1
    assert not settings["element_sell_at_purchase_price"]
    assert settings["transfers_sell_on_fee"] == 0.5  # half_profit_rounded_down

    assert rules.raw["scoring"]["goals"] == scoring["goals_scored"]
    assert rules.raw["scoring"]["clean_sheet"] == scoring["clean_sheets"]
    assert rules.raw["scoring"]["assists"] == scoring["assists"]
    assert rules.raw["scoring"]["appearance"]["gte_60_min"] == scoring["long_play"]
    assert rules.raw["scoring"]["appearance"]["lt_60_min"] == scoring["short_play"]
    dc = rules.raw["scoring"]["defensive_contribution"]
    assert {pos: v["points"] for pos, v in dc.items()} == {
        pos: pts for pos, pts in scoring["defensive_contribution"].items() if pts
    }
    # Assistant manager is gone: no chip entry, no manager scoring.
    assert {c["name"] for c in boot["chips"]} == {"wildcard", "freehit", "bboost", "3xc"}
    for key, value in scoring.items():
        if key.startswith("mng_"):
            values = value.values() if isinstance(value, dict) else [value]
            assert not any(values), f"manager scoring {key} is live: {value}"
    assert rules.raw["chips"]["assistant_manager"]["count"] == 0


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

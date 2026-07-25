"""Weekly all-team report builder — fully offline (fixture payloads, no network).

Locks the defects found in the 2026-07-25 pre-season dry-run:
  - reports were written in the locale codec (cp1252 on Windows): every file was
    invalid UTF-8 and any name outside cp1252 (Petrović) crashed the build
  - date.today() drove the week directory even under --from-snapshot, so a
    point-in-time rebuild landed in the wrong week and used a wall-clock window
  - the 14-day fixture window is empty in pre-season -> 20 files of "no matches"
  - the docstring promised price/ownership movers that were never implemented
  - team-name slugs could collide and silently overwrite another team's file
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from fpl_claude.reports import team_week

# --------------------------------------------------------------------------- fixtures

TEAMS = [
    {"id": 1, "name": "Arsenal", "short_name": "ARS"},
    {"id": 2, "name": "Nott'm Forest", "short_name": "NFO"},
    {"id": 3, "name": "Brighton & Hove", "short_name": "BHA"},
]

PLAYERS = [
    {
        "id": 10, "web_name": "Ødegaard", "team": 1, "element_type": 3, "status": "d",
        "news": "Knock - 75% chance of playing", "chance_of_playing_next_round": 75,
        "selected_by_percent": "12.4", "now_cost": 85,
    },
    {
        "id": 11, "web_name": "Saka", "team": 1, "element_type": 3, "status": "a",
        "news": "", "chance_of_playing_next_round": None,
        "selected_by_percent": "45.3", "now_cost": 100,
    },
    {
        "id": 20, "web_name": "Milenković", "team": 2, "element_type": 2, "status": "i",
        "news": "Hamstring injury - Expected back 23 Aug",
        "chance_of_playing_next_round": 0, "selected_by_percent": "3.1", "now_cost": 55,
    },
    {
        "id": 30, "web_name": "Sánchez", "team": 3, "element_type": 1, "status": "a",
        "news": "", "chance_of_playing_next_round": None,
        "selected_by_percent": "8.0", "now_cost": 50,
    },
]

# GW1 2026-08-21/22, GW2 2026-08-29, GW3 2026-09-04 — all unfinished (pre-season).
PRESEASON_FIXTURES = [
    {"id": 1, "event": 1, "kickoff_time": "2026-08-21T19:00:00Z", "finished": False,
     "team_h": 1, "team_a": 2, "team_h_difficulty": 2, "team_a_difficulty": 5,
     "team_h_score": None, "team_a_score": None},
    {"id": 2, "event": 1, "kickoff_time": "2026-08-22T14:00:00Z", "finished": False,
     "team_h": 3, "team_a": 1, "team_h_difficulty": 4, "team_a_difficulty": 3,
     "team_h_score": None, "team_a_score": None},
    {"id": 3, "event": 2, "kickoff_time": "2026-08-29T14:00:00Z", "finished": False,
     "team_h": 2, "team_a": 3, "team_h_difficulty": 3, "team_a_difficulty": 3,
     "team_h_score": None, "team_a_score": None},
]

PRESEASON_EVENTS = [
    {"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-21T17:30:00Z",
     "finished": False, "is_current": False, "is_next": True},
    {"id": 2, "name": "Gameweek 2", "deadline_time": "2026-08-29T10:30:00Z",
     "finished": False, "is_current": False, "is_next": False},
]


def _bootstrap(events=None, players=None, teams=None) -> dict:
    return {
        "teams": list(teams if teams is not None else TEAMS),
        "elements": [dict(p) for p in (players if players is not None else PLAYERS)],
        "events": list(events if events is not None else PRESEASON_EVENTS),
    }


def _write_snapshot(
    raw_dir: Path,
    day: str,
    bootstrap: dict,
    fixtures: list[dict],
    fetched_at: str | None = None,
) -> Path:
    day_dir = raw_dir / day
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "bootstrap.json").write_text(json.dumps(bootstrap), encoding="utf-8")
    (day_dir / "fixtures.json").write_text(json.dumps(fixtures), encoding="utf-8")
    (day_dir / "meta.json").write_text(
        json.dumps({"fetched_at_utc": fetched_at or f"{day}T09:00:00Z"}), encoding="utf-8"
    )
    return day_dir


@pytest.fixture
def preseason(tmp_path: Path):
    """A pre-season snapshot at 2026-07-25 (26 days before the GW1 deadline)."""
    raw = tmp_path / "raw"
    _write_snapshot(raw, "2026-07-25", _bootstrap(), PRESEASON_FIXTURES)
    return raw


def _build(raw: Path, tmp_path: Path, day: str = "2026-07-25") -> Path:
    return team_week.build_reports(
        from_snapshot=day, out_dir=tmp_path / "out", raw_dir=raw
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ shape & coverage


def test_one_report_per_team_plus_index(preseason: Path, tmp_path: Path):
    out = _build(preseason, tmp_path)
    md = sorted(p.name for p in out.glob("*.md"))
    assert md == ["arsenal.md", "brighton-hove.md", "index.md", "nottm-forest.md"]


def test_index_has_one_row_per_team(preseason: Path, tmp_path: Path):
    out = _build(preseason, tmp_path)
    index = _read(out / "index.md")
    rows = [ln for ln in index.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(rows) == len(TEAMS) + 1  # header row + one per team
    for team in TEAMS:
        assert f"| {team['name']} |" in index


def test_index_reports_gw1_opponent_and_opening_fdr(preseason: Path, tmp_path: Path):
    index = _read(_build(preseason, tmp_path) / "index.md")
    assert "| Arsenal | NFO (H) |" in index
    assert "| Nott'm Forest | ARS (A) |" in index
    assert "GW1 fixture" in index  # pre-season header, not "PL games last 7d"


# ----------------------------------------------------------------------- encoding


def test_reports_are_valid_utf8_with_lf(preseason: Path, tmp_path: Path):
    """Every file must decode as UTF-8 — the cp1252 default corrupted all 21."""
    out = _build(preseason, tmp_path)
    for path in out.glob("*.md"):
        raw = path.read_bytes()
        raw.decode("utf-8")  # raises on the pre-fix output
        assert b"\r" not in raw, f"{path.name} has CRLF line endings"


def test_non_ascii_names_round_trip(preseason: Path, tmp_path: Path):
    out = _build(preseason, tmp_path)
    assert "Ødegaard" in _read(out / "arsenal.md")
    assert "Milenković" in _read(out / "nottm-forest.md")  # crashed under cp1252


# ------------------------------------------------------------------------- flags


def test_flagged_player_rendering(preseason: Path, tmp_path: Path):
    arsenal = _read(_build(preseason, tmp_path) / "arsenal.md")
    assert "**Ødegaard** (MID, 12.4% owned): DOUBTFUL, 75% next round" in arsenal
    assert "Knock - 75% chance of playing" in arsenal
    assert "Saka" not in arsenal  # available, unflagged, no news


def test_team_without_flags_says_none(preseason: Path, tmp_path: Path):
    brighton = _read(_build(preseason, tmp_path) / "brighton-hove.md")
    assert "## Flagged players (FPL API)\n- none" in brighton


# ------------------------------------------------------------- pre-season / windows


def test_preseason_says_season_not_started_and_shows_opening_run(
    preseason: Path, tmp_path: Path
):
    arsenal = _read(_build(preseason, tmp_path) / "arsenal.md")
    assert "season not started" in arsenal
    assert "no PL matches in the window" not in arsenal
    assert "opening run" in arsenal
    assert "GW1 Fri 21 Aug: Nott'm Forest (H, FDR 2)" in arsenal
    assert "GW1 Sat 22 Aug: Brighton & Hove (A, FDR 3)" in arsenal
    assert "avg FDR 2.5 over 2" in arsenal
    assert "## Pre-season (filled by skill)" in arsenal


def test_preseason_index_carries_the_next_deadline(preseason: Path, tmp_path: Path):
    index = _read(_build(preseason, tmp_path) / "index.md")
    assert "pre-season" in index
    assert "GW1 Fri 21 Aug 17:30 UTC" in index
    assert "(27d away)" in index


def test_in_season_window_uses_results_and_14_day_fixtures(tmp_path: Path):
    """Snapshot taken 2026-08-24: GW1 played (in the 7d window), GW2 upcoming."""
    fixtures = [dict(fx) for fx in PRESEASON_FIXTURES]
    fixtures[0].update(finished=True, team_h_score=2, team_a_score=1)
    fixtures[1].update(finished=True, team_h_score=0, team_a_score=3)
    events = [dict(e) for e in PRESEASON_EVENTS]
    events[0].update(finished=True, is_current=True, is_next=False)
    raw = tmp_path / "raw"
    _write_snapshot(
        raw, "2026-08-24", _bootstrap(events=events), fixtures, "2026-08-24T09:00:00Z"
    )

    out = _build(raw, tmp_path, day="2026-08-24")
    arsenal = _read(out / "arsenal.md")
    assert "Fri 21 Aug: Arsenal 2–1 Nott'm Forest" in arsenal
    assert "Sat 22 Aug: Brighton & Hove 0–3 Arsenal" in arsenal
    assert "opening run" not in arsenal
    index = _read(out / "index.md")
    assert "PL games last 7d" in index
    assert "| Arsenal | 2 | 0 |" in index  # 2 played, no PL game within 14d for ARS


def test_no_fixtures_at_all_degrades_cleanly(tmp_path: Path):
    raw = tmp_path / "raw"
    _write_snapshot(raw, "2026-07-25", _bootstrap(), [])
    arsenal = _read(_build(raw, tmp_path) / "arsenal.md")
    assert "no PL fixtures scheduled" in arsenal


# ------------------------------------------------------------- snapshot date vs today


def test_week_directory_comes_from_the_snapshot_not_today(tmp_path: Path):
    raw = tmp_path / "raw"
    _write_snapshot(raw, "2026-03-02", _bootstrap(), PRESEASON_FIXTURES)
    out = _build(raw, tmp_path, day="2026-03-02")
    assert out.name == "2026-10" == f"{date(2026, 3, 2):%G-%V}"
    assert "week 2026-W10" in _read(out / "index.md")
    # the snapshot is months from any plausible run date — a wall-clock week would differ
    assert "2026-07" not in out.name


def test_snapshot_instant_drives_the_lookback_window(tmp_path: Path):
    """meta.json's fetched_at is 'now' — a wall-clock 'now' would find no results."""
    fixtures = [dict(PRESEASON_FIXTURES[0])]
    fixtures[0].update(finished=True, team_h_score=1, team_a_score=1)
    events = [dict(e) for e in PRESEASON_EVENTS]
    events[0].update(finished=True, is_current=True)
    raw = tmp_path / "raw"
    _write_snapshot(
        raw, "2026-08-23", _bootstrap(events=events), fixtures, "2026-08-23T08:00:00Z"
    )
    arsenal = _read(_build(raw, tmp_path, day="2026-08-23") / "arsenal.md")
    assert "Arsenal 1–1 Nott'm Forest" in arsenal


def test_missing_meta_falls_back_to_midday_of_the_snapshot_date(tmp_path: Path):
    raw = tmp_path / "raw"
    day = _write_snapshot(raw, "2026-07-25", _bootstrap(), PRESEASON_FIXTURES)
    (day / "meta.json").unlink()
    out = _build(raw, tmp_path)
    assert out.name == "2026-30"


# ------------------------------------------------------------------------- movers


def test_movers_without_a_prior_snapshot(preseason: Path, tmp_path: Path):
    arsenal = _read(_build(preseason, tmp_path) / "arsenal.md")
    assert "no prior snapshot" in arsenal
    assert "## Price & ownership movers" in arsenal


def test_movers_against_a_prior_snapshot(tmp_path: Path):
    raw = tmp_path / "raw"
    prior = _bootstrap()
    _write_snapshot(raw, "2026-07-18", prior, PRESEASON_FIXTURES)

    current = _bootstrap()
    by_id = {p["id"]: p for p in current["elements"]}
    by_id[10]["now_cost"] = 86              # Ødegaard rises 0.1
    by_id[11]["now_cost"] = 99              # Saka falls 0.1
    by_id[11]["selected_by_percent"] = "41.0"  # and sheds 4.3pp
    by_id[20]["selected_by_percent"] = "3.2"   # sub-threshold: must not appear
    current["elements"].append({
        "id": 12, "web_name": "N'Dri", "team": 1, "element_type": 4, "status": "a",
        "news": "", "chance_of_playing_next_round": None,
        "selected_by_percent": "0.4", "now_cost": 45,
    })
    _write_snapshot(raw, "2026-07-25", current, PRESEASON_FIXTURES)

    out = _build(raw, tmp_path)
    arsenal = _read(out / "arsenal.md")
    assert "vs snapshot `2026-07-18`" in arsenal
    assert "price +1 → £8.6m — **Ødegaard**" in arsenal
    assert "price -1 → £9.9m — **Saka**" in arsenal
    assert "ownership -4.3pp → 41.0% — **Saka**" in arsenal
    assert "NEW in the game — **N'Dri** (FWD, £4.5m)" in arsenal

    forest = _read(out / "nottm-forest.md")
    assert "no price or ownership movement above threshold" in forest
    assert "| Arsenal | NFO (H) | 2.5 | 1 | 4 |" in _read(out / "index.md")


def test_prior_snapshot_is_the_newest_strictly_older_one(tmp_path: Path):
    raw = tmp_path / "raw"
    for day in ("2026-07-10", "2026-07-18", "2026-07-25", "2026-08-01"):
        _write_snapshot(raw, day, _bootstrap(), PRESEASON_FIXTURES)
    (raw / "not-a-date").mkdir()
    assert team_week.find_prior_snapshot(raw, date(2026, 7, 25)).name == "2026-07-18"
    assert team_week.find_prior_snapshot(raw, date(2026, 7, 10)) is None
    assert team_week.find_prior_snapshot(tmp_path / "nope", date(2026, 7, 25)) is None


# --------------------------------------------------------------------------- slugs


def test_slugify_folds_accents_and_punctuation():
    assert team_week.slugify("Nott'm Forest") == "nottm-forest"
    assert team_week.slugify("Brighton & Hove") == "brighton-hove"
    assert team_week.slugify("Bayer 04 Leverkusen") == "bayer-04-leverkusen"
    assert team_week.slugify("Köln") == "koln"
    assert team_week.slugify("!!!") == "team"


def test_slug_collisions_do_not_overwrite(tmp_path: Path):
    teams = [
        {"id": 1, "name": "Leeds", "short_name": "LEE"},
        {"id": 2, "name": "L.E.E.D.S.", "short_name": "LDS"},
    ]
    raw = tmp_path / "raw"
    _write_snapshot(raw, "2026-07-25", _bootstrap(teams=teams, players=[]), [])
    out = _build(raw, tmp_path)
    assert {p.name for p in out.glob("*.md")} == {"index.md", "leeds.md", "leeds-2.md"}


# ----------------------------------------------------------------------------- cli


def test_cli_accepts_out_dir_and_raw_dir(preseason: Path, tmp_path: Path, capsys):
    dest = tmp_path / "cli-out"
    team_week.main(
        ["--from-snapshot", "2026-07-25", "--out-dir", str(dest), "--raw-dir", str(preseason)]
    )
    assert (dest / "2026-30" / "index.md").exists()
    assert "reports written" in capsys.readouterr().out

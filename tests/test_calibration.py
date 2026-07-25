"""Tests for the automatic /fpl-review calibration loop (backlog A3).

Offline and deterministic by construction: every frame is synthesised into
`tmp_path`. `db/projections/`, `db/raw/` and `db/backtest/` are gitignored and
may be entirely absent on a fresh clone, and the live FPL API is never reachable
from a test run — so the actuals seam is exercised with an injected payload, not
the network.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from fpl_claude.reports import calibration as cal

DEADLINE = datetime(2026, 11, 28, 18, 30, tzinfo=UTC)
GW = 12


# ------------------------------------------------------------------ fixtures


def write_projections(path: Path, rows: list[dict], gw: int = GW) -> Path:
    """A minimal `db/projections/{date}.csv` — the columns the real pipeline
    writes that this module reads."""
    frame = pd.DataFrame(
        [
            {
                "id": r["id"],
                "web_name": r.get("web_name", f"P{r['id']}"),
                "team": r.get("team", "Arsenal"),
                "position": r.get("position", "MID"),
                "price": r.get("price", 6.0),
                f"xpts_gw{gw}": r["predicted"],
                "xpts_horizon": r["predicted"] * 4,
                "exp_minutes_gw": r.get("exp_minutes_gw", 85.0),
                "minutes_confidence": r.get("minutes_confidence", "high"),
                "ep_next": r.get("ep_next", float("nan")),
            }
            for r in rows
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_backtest_players(path: Path, rows: list[dict]) -> Path:
    """A `gw{NN}_players.csv` in the committed backtest archive's schema."""
    frame = pd.DataFrame(
        [
            {
                "id": r["id"],
                "web_name": r.get("web_name", f"P{r['id']}"),
                "team": r.get("team", "Arsenal"),
                "position": r.get("position", "MID"),
                "price": r.get("price", 6.0),
                "predicted": r["predicted"],
                "actual": r["actual"],
                "minutes": r.get("minutes", 90),
                "role": r["role"],
                "played_after_subs": r.get("played_after_subs", True),
            }
            for r in rows
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def set_mtime(path: Path, when: datetime) -> None:
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))


def owned_frame(rows: list[dict]) -> pd.DataFrame:
    """Joined owned-squad rows straight into `slot_split` (predicted/actual/role)."""
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- the join


def test_join_reports_players_present_on_one_side_only(tmp_path):
    snap = write_projections(
        tmp_path / "2026-11-27.csv",
        [
            {"id": 1, "predicted": 4.0},
            {"id": 2, "predicted": 3.0},
            {"id": 3, "predicted": 2.0},
        ],
    )
    predicted = cal.load_predictions(snap, GW)
    actual = pd.DataFrame(
        {"id": [1, 2, 99], "actual": [5.0, 2.0, 7.0], "minutes": [90, 90, 90]}
    )
    joined, report = cal.join_predicted_actual(predicted, actual)

    assert report.matched == 2  # ids 1 and 2
    assert report.predicted_only == 1  # id 3 projected, never appeared in actuals
    assert report.actual_only == 1  # id 99 played, was never projected
    assert set(joined["id"]) == {1, 2}
    # error convention: actual - predicted (positive = we UNDER-predicted)
    assert joined.set_index("id").loc[1, "error"] == pytest.approx(5.0 - 4.0)


def test_load_predictions_refuses_a_snapshot_that_does_not_cover_the_gw(tmp_path):
    snap = write_projections(tmp_path / "2026-11-27.csv", [{"id": 1, "predicted": 4.0}], gw=5)
    with pytest.raises(KeyError, match="xpts_gw12"):
        cal.load_predictions(snap, GW)


# ------------------------------------------------- point-in-time snapshot pick


def test_select_snapshot_takes_the_newest_file_at_or_before_the_deadline(tmp_path):
    for day in ("2026-11-20", "2026-11-27", "2026-11-25"):
        write_projections(tmp_path / f"{day}.csv", [{"id": 1, "predicted": 4.0}])
    choice = cal.select_snapshot(DEADLINE, projections_dir=tmp_path)
    assert choice.path.name == "2026-11-27.csv"
    assert choice.verified is True
    assert choice.rejected == ()


def test_select_snapshot_rejects_and_warns_about_a_post_deadline_file(tmp_path):
    write_projections(tmp_path / "2026-11-27.csv", [{"id": 1, "predicted": 4.0}])
    write_projections(tmp_path / "2026-11-30.csv", [{"id": 1, "predicted": 4.0}])
    with pytest.warns(cal.PointInTimeWarning, match="post-deadline"):
        choice = cal.select_snapshot(DEADLINE, projections_dir=tmp_path)
    assert choice.path.name == "2026-11-27.csv"  # the later file is NOT used
    assert choice.rejected == ("2026-11-30.csv",)


def test_select_snapshot_refuses_when_every_candidate_is_post_deadline(tmp_path):
    write_projections(tmp_path / "2026-11-30.csv", [{"id": 1, "predicted": 4.0}])
    with pytest.warns(cal.PointInTimeWarning), pytest.raises(cal.PointInTimeError):
        cal.select_snapshot(DEADLINE, projections_dir=tmp_path)


def test_deadline_day_file_written_before_the_deadline_is_accepted(tmp_path):
    path = write_projections(tmp_path / "2026-11-28.csv", [{"id": 1, "predicted": 4.0}])
    set_mtime(path, datetime(2026, 11, 28, 9, 0, tzinfo=UTC))
    choice = cal.select_snapshot(DEADLINE, projections_dir=tmp_path)
    assert choice.path.name == "2026-11-28.csv"
    assert choice.verified is True


def test_deadline_day_file_written_after_the_deadline_is_rejected(tmp_path):
    early = write_projections(tmp_path / "2026-11-26.csv", [{"id": 1, "predicted": 4.0}])
    late = write_projections(tmp_path / "2026-11-28.csv", [{"id": 1, "predicted": 4.0}])
    set_mtime(early, datetime(2026, 11, 26, 9, 0, tzinfo=UTC))
    set_mtime(late, datetime(2026, 11, 28, 20, 15, tzinfo=UTC))  # after the 18:30 deadline
    with pytest.warns(cal.PointInTimeWarning):
        choice = cal.select_snapshot(DEADLINE, projections_dir=tmp_path)
    assert choice.path.name == "2026-11-26.csv"
    assert choice.rejected == ("2026-11-28.csv",)


def test_explicit_post_deadline_snapshot_raises_unless_forced(tmp_path):
    path = write_projections(tmp_path / "2026-11-30.csv", [{"id": 1, "predicted": 4.0}])
    with pytest.raises(cal.PointInTimeError, match="AFTER the deadline"):
        cal.select_snapshot(DEADLINE, explicit=path)
    with pytest.warns(cal.PointInTimeWarning):
        forced = cal.select_snapshot(DEADLINE, explicit=path, allow_post_deadline=True)
    assert forced.verified is False


def test_no_deadline_available_warns_and_flags_the_choice_unverified(tmp_path):
    write_projections(tmp_path / "2026-11-27.csv", [{"id": 1, "predicted": 4.0}])
    with pytest.warns(cal.PointInTimeWarning, match="NOT verified"):
        choice = cal.select_snapshot(None, projections_dir=tmp_path)
    assert choice.verified is False
    assert "NOT verified" in cal._snapshot_lines(_calibration_for(tmp_path, choice))[0]


def _calibration_for(tmp_path: Path, choice: cal.SnapshotChoice) -> cal.GwCalibration:
    predictions = cal.load_predictions(choice.path, GW)
    actuals = pd.DataFrame({"id": [1], "actual": [6.0], "minutes": [90]})
    return cal.calibrate_gw(GW, predictions, actuals, choice, "unit test")


# ------------------------------------------------ base XI vs captain-slot split


CAPTAIN_SQUAD = [
    {"id": 1, "web_name": "Cap", "position": "FWD", "predicted": 7.0, "actual": 12.0,
     "minutes": 90, "role": "C"},
    {"id": 2, "web_name": "Vice", "position": "MID", "predicted": 6.0, "actual": 2.0,
     "minutes": 90, "role": "V"},
    {"id": 3, "web_name": "Xi", "position": "DEF", "predicted": 4.0, "actual": 6.0,
     "minutes": 90, "role": "XI"},
    {"id": 4, "web_name": "Bench", "position": "GKP", "predicted": 3.0, "actual": 9.0,
     "minutes": 90, "role": "bench"},
]


def test_slot_split_counts_the_captain_exactly_twice_and_never_in_the_base():
    split = cal.slot_split(owned_frame(CAPTAIN_SQUAD))
    # base XI = the fielded players EXCEPT the captain (vice + XI), bench excluded
    assert split.base_xi_predicted == pytest.approx(6.0 + 4.0)
    assert split.base_xi_actual == pytest.approx(2.0 + 6.0)
    # captain slot carries BOTH copies of him, and nothing else
    assert split.captain_slot_predicted == pytest.approx(2 * 7.0)
    assert split.captain_slot_actual == pytest.approx(2 * 12.0)
    # base + slot == total, with the captain appearing exactly captain_mult times
    assert split.total_predicted == pytest.approx(6.0 + 4.0 + 2 * 7.0)
    assert split.total_predicted == pytest.approx(
        split.base_xi_predicted + split.captain_slot_predicted
    )
    assert split.total_error == pytest.approx(split.base_xi_error + split.captain_slot_error)


def test_slot_split_a2_recut_reconciles_to_the_same_total():
    """calibration.md's headline cut (XI with the captain x1, plus the extra
    copy) must partition the SAME total as the memo cut — otherwise the live log
    and the 20-GW backtest study are not comparable."""
    split = cal.slot_split(owned_frame(CAPTAIN_SQUAD))
    assert split.xi_capx1_predicted + split.captain_extra_predicted == pytest.approx(
        split.total_predicted
    )
    assert split.xi_capx1_actual + split.captain_extra_actual == pytest.approx(
        split.total_actual
    )
    assert split.xi_capx1_error + split.captain_extra_error == pytest.approx(split.total_error)


def test_slot_split_triple_captain_triples_only_the_captain_slot():
    split = cal.slot_split(owned_frame(CAPTAIN_SQUAD), chip="triple_captain")
    assert split.captain_mult == 3
    assert split.captain_slot_predicted == pytest.approx(3 * 7.0)
    assert split.base_xi_predicted == pytest.approx(6.0 + 4.0)  # base is untouched
    assert split.total_predicted == pytest.approx(10.0 + 21.0)


def test_slot_split_bench_boost_counts_all_fifteen():
    split = cal.slot_split(owned_frame(CAPTAIN_SQUAD), chip="bench_boost")
    assert split.counted == 4
    assert split.base_xi_predicted == pytest.approx(6.0 + 4.0 + 3.0)  # bench now counts


def test_slot_split_hands_the_armband_to_the_vice_on_a_zero_minute_captain():
    squad = [dict(r) for r in CAPTAIN_SQUAD]
    squad[0]["minutes"] = 0
    squad[0]["actual"] = 0.0
    split = cal.slot_split(owned_frame(squad))
    assert split.captain_switched is True
    assert split.effective_captain_name == "Vice"
    # predicted side still prices the PICKED captain; actual side the vice
    assert split.captain_slot_predicted == pytest.approx(2 * 7.0)
    assert split.captain_slot_actual == pytest.approx(2 * 2.0)


# --------------------------------------------------------------- ep_next NaN


def test_benchmark_is_nan_safe_and_reports_its_own_sample():
    joined = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "web_name": ["A", "B", "C"],
            "position": ["MID", "DEF", "FWD"],
            "predicted": [4.0, 3.0, 5.0],
            "ep_next": [3.0, float("nan"), 6.0],
            "actual": [6.0, 2.0, 6.0],
        }
    )
    joined["error"] = joined["actual"] - joined["predicted"]
    joined["ep_error"] = joined["actual"] - joined["ep_next"]
    bench = cal.benchmark_ep_next(joined)

    assert bench.n == 2  # the NaN row is dropped, not zero-filled
    assert bench.fpl.n == 2
    # id 3: ours 5.0 vs actual 6 (err +1); FPL 6.0 (err 0) -> FPL closer
    assert bench.fpl_closer == 1
    assert bench.ours_closer == 1
    assert list(bench.fpl_wins["id"]) == [3]


def test_benchmark_absent_ep_next_says_so_instead_of_inventing_a_comparison():
    joined = pd.DataFrame(
        {
            "id": [1],
            "web_name": ["A"],
            "position": ["MID"],
            "predicted": [4.0],
            "ep_next": [float("nan")],
            "actual": [6.0],
        }
    )
    joined["error"] = joined["actual"] - joined["predicted"]
    joined["ep_error"] = joined["actual"] - joined["ep_next"]
    bench = cal.benchmark_ep_next(joined)
    assert bench.n == 0
    assert "absent from this snapshot" in "\n".join(cal._benchmark_lines(bench))


# ------------------------------------------------------------------ statistics


def test_error_stats_follows_the_a2_t_statistic_convention():
    # mean +2, sample std 1 over n=5 -> SE = 1/sqrt(5) = 0.4472, t = +4.47
    stats = cal.error_stats([1.0, 2.0, 3.0, 2.0, 2.0], "unit")
    assert stats.n == 5
    assert stats.mean_error == pytest.approx(2.0)
    assert stats.mae == pytest.approx(2.0)
    assert stats.se == pytest.approx(0.31622776, rel=1e-4)
    assert stats.t == pytest.approx(6.32455, rel=1e-4)
    assert stats.significant is True


def test_error_stats_calls_a_within_noise_mean_not_significant():
    stats = cal.error_stats([10.0, -9.0, 8.0, -7.0, 2.0], "unit")
    assert abs(stats.mean_error) > 0
    assert stats.significant is False


# ------------------------------------------------------------- actuals seams


def test_live_actuals_reads_the_event_live_payload_without_the_network():
    payload = {
        "elements": [
            {"id": 1, "stats": {"total_points": 9, "minutes": 90}},
            {"id": 2, "stats": {"total_points": 0, "minutes": 0}},
        ]
    }
    frame = cal.live_actuals(GW, fetch=lambda gw: payload)
    assert list(frame["id"]) == [1, 2]
    assert list(frame["actual"]) == [9.0, 0.0]
    assert list(frame["minutes"]) == [90.0, 0.0]


def test_backtest_actuals_carries_the_role_column(tmp_path):
    path = write_backtest_players(tmp_path / "gw12_players.csv", CAPTAIN_SQUAD)
    frame = cal.backtest_actuals(path)
    assert set(frame.columns) == {"id", "actual", "minutes", "role"}
    assert frame.set_index("id").loc[1, "role"] == "C"


# ------------------------------------------------------- end to end + the log


def _end_to_end(tmp_path: Path, gw: int = GW) -> cal.GwCalibration:
    snap_path = write_projections(
        tmp_path / "proj" / "2026-11-27.csv",
        [
            {"id": 1, "web_name": "Cap", "position": "FWD", "predicted": 7.0, "ep_next": 6.5},
            {"id": 2, "web_name": "Vice", "position": "MID", "predicted": 6.0, "ep_next": 5.0},
            {"id": 3, "web_name": "Xi", "position": "DEF", "predicted": 4.0,
             "ep_next": float("nan")},
            {"id": 4, "web_name": "Bench", "position": "GKP", "predicted": 3.0, "ep_next": 3.5},
            {"id": 5, "web_name": "Other", "position": "MID", "predicted": 2.0,
             "ep_next": 2.0},  # projected, never owned
        ],
        gw=gw,
    )
    choice = cal.select_snapshot(DEADLINE, projections_dir=snap_path.parent)
    players = write_backtest_players(tmp_path / f"gw{gw:02d}_players.csv", CAPTAIN_SQUAD)
    return cal.calibrate_gw(
        gw,
        cal.load_predictions(choice.path, gw),
        cal.backtest_actuals(players),
        choice,
        f"backtest archive `{players.name}`",
    )


def test_end_to_end_separates_owned_players_from_the_whole_pool(tmp_path):
    result = _end_to_end(tmp_path)
    pool_all = result.pool_stats[0]
    owned_all = result.owned_stats[0]
    assert pool_all.n == 4  # id 5 was projected but has no actual -> dropped, counted
    assert result.join.predicted_only == 1
    assert owned_all.n == 4
    assert result.slots is not None
    assert result.slots.captain_name == "Cap"


def test_append_log_creates_then_appends_without_overwriting(tmp_path):
    log = tmp_path / "calibration.md"
    first = _end_to_end(tmp_path, gw=GW)
    cal.append_log(first, log)
    after_first = log.read_text(encoding="utf-8")
    assert after_first.startswith("# Calibration log")
    assert f"## GW{GW} —" in after_first

    cal.append_log(_end_to_end(tmp_path, gw=GW + 1), log)
    after_second = log.read_text(encoding="utf-8")

    # every byte of the first write survives, and the header is written ONCE
    assert after_first in after_second
    assert after_second.count("# Calibration log") == 1
    assert f"## GW{GW} —" in after_second
    assert f"## GW{GW + 1} —" in after_second


def test_relogging_a_gameweek_appends_a_superseding_section_not_a_rewrite(tmp_path):
    log = tmp_path / "calibration.md"
    result = _end_to_end(tmp_path)
    cal.append_log(result, log)
    cal.append_log(result, log)
    text = log.read_text(encoding="utf-8")
    assert text.count(f"## GW{GW} —") == 2
    assert "supersedes" in text


def test_rendered_section_records_the_snapshot_used_and_the_slot_split(tmp_path):
    section = cal.render_section(_end_to_end(tmp_path))
    assert "2026-11-27.csv" in section  # the audit trail: WHICH snapshot predicted this
    assert "point-in-time **verified**" in section
    assert "base XI" in section and "captain slot" in section
    assert "FPL `ep_next` benchmark" in section

"""Chip TIMING (Phase 3b advisory) — offline, synthetic fixtures + a held pool.

Covers the timing layer that sits on top of the chip mechanics: DGW/BGW
detection from a fixtures table, the per-GW chip-EV surface (TC extra = captain's
single-GW xpts; BB extra = the four bench players' xpts; minutes nailedness), and
the advice gate that encodes the knowledge.md rule (TC on a standout/DGW captain;
BB only on a nailed DGW; WC/FH on a 4+ change need or a BGW/DGW), one-per-half.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fpl_claude.optimize.chip_timing import (
    BB_MIN_EXTRA_EV,
    TC_STANDOUT_XPTS,
    WC_CHANGE_THRESHOLD,
    ChipAdvice,
    GwChipSurface,
    GwDoubleBlank,
    advise,
    chip_half,
    chip_surface,
    detect_double_blank,
)
from fpl_claude.rules.engine import Ruleset


@pytest.fixture(scope="module")
def lineup() -> dict:
    return Ruleset.load("2025-26").raw["lineup"]  # 1 GK, >=3 DEF, >=2 MID, >=1 FWD


# ------------------------------------------------------------------ DGW / BGW


def _fixtures() -> list[dict]:
    """Six teams (1-6). GW1 normal (each once); GW2 doubles teams 1 & 2; GW3
    blanks teams 3-6. One NaN-event row that must be skipped."""
    return [
        {"event": 1, "team_h": 1, "team_a": 2},
        {"event": 1, "team_h": 3, "team_a": 4},
        {"event": 1, "team_h": 5, "team_a": 6},
        {"event": 2, "team_h": 1, "team_a": 3},
        {"event": 2, "team_h": 1, "team_a": 4},  # team 1 plays twice
        {"event": 2, "team_h": 2, "team_a": 5},
        {"event": 2, "team_h": 2, "team_a": 6},  # team 2 plays twice
        {"event": 3, "team_h": 1, "team_a": 2},  # 3,4,5,6 blank
        {"event": None, "team_h": 1, "team_a": 2},  # unscheduled — skipped
    ]


def test_detect_double_blank_normal_double_blank():
    db = detect_double_blank(_fixtures())
    # GW1: everyone once — no doubles, no blanks.
    assert db[1].dgw_teams == frozenset() and db[1].bgw_teams == frozenset()
    # GW2: teams 1 & 2 double; nobody blanks.
    assert db[2].dgw_teams == frozenset({1, 2}) and db[2].bgw_teams == frozenset()
    # GW3: only 1 & 2 play; 3-6 blank.
    assert db[3].dgw_teams == frozenset()
    assert db[3].bgw_teams == frozenset({3, 4, 5, 6})


def test_detect_double_blank_maps_ids_to_names():
    names = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F"}
    db = detect_double_blank(_fixtures(), names)
    assert db[2].dgw_teams == frozenset({"A", "B"})
    assert db[3].bgw_teams == frozenset({"C", "D", "E", "F"})


def test_chip_half_boundary():
    assert chip_half(19) == 1 and chip_half(20) == 2
    assert chip_half(1) == 1 and chip_half(38) == 2


# --------------------------------------------------------------- EV surface


def _held_pool(low_min_ids: set[int] = frozenset()) -> pd.DataFrame:
    """A held squad-15 (2 GKP/5 DEF/5 MID/3 FWD) with scores chosen so the XI/
    bench split is deterministic: the four lowest scorers (ids 2, 7, 12, 15) are
    always benched → bench sum 0.5+0.6+0.7+0.8 = 2.6, captain = id 8 (9.0).
    Six players (incl. the captain) sit on team DBL to exercise DGW counting."""
    dbl = {8, 3, 4, 5, 9, 13}  # 6 players on the doubling club, incl. the captain
    specs = [
        (1, "G_A", "GKP", 5.0),
        (2, "G_B", "GKP", 0.5),   # 2nd keeper — always benched
        (3, "D1", "DEF", 4.5),
        (4, "D2", "DEF", 4.4),
        (5, "D3", "DEF", 4.3),
        (6, "D4", "DEF", 4.2),
        (7, "D5", "DEF", 0.6),    # benched
        (8, "M1", "MID", 9.0),    # captain candidate
        (9, "M2", "MID", 4.9),
        (10, "M3", "MID", 4.8),
        (11, "M4", "MID", 4.7),
        (12, "M5", "MID", 0.7),   # benched
        (13, "F1", "FWD", 5.5),
        (14, "F2", "FWD", 5.4),
        (15, "F3", "FWD", 0.8),   # benched
    ]
    rows = [
        {
            "id": i,
            "web_name": n,
            "team": "DBL" if i in dbl else "SNG",
            "position": p,
            "price": 5.0,
            "exp_minutes_gw": 20 if i in low_min_ids else 90,
            "xpts_gw1": s,
        }
        for (i, n, p, s) in specs
    ]
    return pd.DataFrame(rows)


def test_chip_surface_tc_bb_arithmetic(lineup):
    pool = _held_pool()
    s = chip_surface(pool, list(pool["id"]), lineup)[0]
    assert s.gw == 1
    assert s.tc_captain == 8
    assert s.tc_extra == pytest.approx(9.0)  # captain's single-GW xpts (the +1x)
    assert s.bb_extra == pytest.approx(2.6, abs=0.01)  # the four benched players
    assert set(s.bb_bench) == {2, 7, 12, 15}
    assert s.bb_nonnailed == 0  # everyone projected 90 minutes


def test_chip_surface_nailedness_flags_low_minutes(lineup):
    # Two BENCH slots (d5, m5) drop to 20' expected minutes → two non-nailed.
    pool = _held_pool(low_min_ids={7, 12})
    s = chip_surface(pool, list(pool["id"]), lineup)[0]
    assert s.bb_nonnailed == 2
    # A low-minute STARTER (captain) must not count against BB nailedness.
    pool2 = _held_pool(low_min_ids={8})
    assert chip_surface(pool2, list(pool2["id"]), lineup)[0].bb_nonnailed == 0


def test_chip_surface_dgw_annotation(lineup):
    pool = _held_pool()
    db = {1: GwDoubleBlank(1, frozenset({"DBL"}), frozenset())}
    s = chip_surface(pool, list(pool["id"]), lineup, db)[0]
    assert s.n_doublers == 6  # the six DBL players
    assert s.n_blankers == 0
    assert s.tc_captain_dgw is True  # captain (id 8) sits on the doubling club


def test_chip_surface_blank_kills_bench_nailedness(lineup):
    pool = _held_pool()
    # Blank the SNG club — the bench (2,7,12,15) all sit on SNG → all non-nailed.
    db = {1: GwDoubleBlank(1, frozenset(), frozenset({"SNG"}))}
    s = chip_surface(pool, list(pool["id"]), lineup, db)[0]
    assert s.n_blankers == 9
    assert s.bb_nonnailed == 4  # every bench slot blanks


# ------------------------------------------------------------------ advice


def _surf(
    gw: int = 21,
    tc_extra: float = 5.0,
    tc_captain_dgw: bool = False,
    bb_extra: float = 8.0,
    bb_nonnailed: int = 0,
    n_doublers: int = 0,
    n_blankers: int = 0,
) -> GwChipSurface:
    return GwChipSurface(
        gw=gw, tc_extra=tc_extra, tc_captain=8, tc_captain_name="M1",
        tc_captain_dgw=tc_captain_dgw, bb_extra=bb_extra, bb_bench=(2, 7, 12, 15),
        bb_nonnailed=bb_nonnailed, n_doublers=n_doublers, n_blankers=n_blankers,
    )


def _advice(surface, chips_used=(), current_gw=21, change_need=None) -> dict[str, ChipAdvice]:
    return advise(surface, list(chips_used), current_gw, change_need=change_need)


def test_advise_tc_on_dgw_captain():
    # A modest projection still triggers TC when the captain's club doubles.
    adv = _advice([_surf(gw=21, tc_extra=6.0, tc_captain_dgw=True)])["triple_captain"]
    assert adv.verdict == "advise" and adv.target_gw == 21 and "DGW" in adv.reason


def test_advise_tc_on_standout_single_fixture():
    adv = _advice([_surf(gw=21, tc_extra=8.5)])["triple_captain"]
    assert adv.verdict == "advise" and "standout" in adv.reason


def test_advise_tc_threshold_edge():
    assert _advice([_surf(tc_extra=7.99)])["triple_captain"].verdict == "hold"
    assert _advice([_surf(tc_extra=TC_STANDOUT_XPTS)])["triple_captain"].verdict == "advise"


def test_advise_bb_on_nailed_dgw():
    s = _surf(gw=21, n_doublers=8, bb_nonnailed=0, bb_extra=15.0)
    adv = _advice([s])["bench_boost"]
    assert adv.verdict == "advise" and adv.target_gw == 21 and "DGW" in adv.reason


def test_advise_bb_blocked_by_nonnailed_bench():
    s = _surf(gw=21, n_doublers=8, bb_nonnailed=2, bb_extra=15.0)
    adv = _advice([s])["bench_boost"]
    assert adv.verdict == "hold" and "non-nailed" in adv.reason


def test_advise_bb_blocked_without_dgw_reports_both_clauses():
    # Mirrors the memo's negative form: nailedness AND the missing DGW.
    s = _surf(gw=21, n_doublers=0, bb_nonnailed=2, bb_extra=10.0)
    adv = _advice([s])["bench_boost"]
    assert adv.verdict == "hold"
    assert "non-nailed" in adv.reason and "no DGW in horizon" in adv.reason


def test_advise_bb_ev_floor_edge():
    below = _surf(gw=21, n_doublers=8, bb_nonnailed=0, bb_extra=BB_MIN_EXTRA_EV - 0.01)
    at = _surf(gw=21, n_doublers=8, bb_nonnailed=0, bb_extra=BB_MIN_EXTRA_EV)
    assert _advice([below])["bench_boost"].verdict == "hold"
    assert _advice([at])["bench_boost"].verdict == "advise"


def test_advise_wc_on_change_need():
    assert _advice([_surf()], change_need=WC_CHANGE_THRESHOLD)["wildcard"].verdict == "advise"
    assert _advice([_surf()], change_need=WC_CHANGE_THRESHOLD - 1)["wildcard"].verdict == "hold"


def test_advise_wc_fh_on_blank():
    s = _surf(gw=21, n_blankers=3)
    fh = _advice([s])["free_hit"]
    wc = _advice([s], change_need=0)["wildcard"]
    assert fh.verdict == "advise" and "BGW" in fh.reason
    assert wc.verdict == "advise" and "BGW" in wc.reason


def test_advise_fh_holds_without_fixture_event():
    # A pure reshape need is a wildcard, never a free hit.
    adv = _advice([_surf()], change_need=6)["free_hit"]
    assert adv.verdict == "hold" and "no BGW/DGW" in adv.reason


def test_advise_inventory_exhaustion_same_half():
    # TC already spent at GW21 (half 2) blocks a GW25 (half 2) recommendation.
    adv = _advice(
        [_surf(gw=25, tc_extra=10.0, tc_captain_dgw=True)],
        chips_used=["triple_captain@21"],
        current_gw=25,
    )["triple_captain"]
    assert adv.verdict == "hold" and "already used" in adv.reason


def test_advise_half_reset_unblocks():
    # A half-1 TC (GW10) does NOT block the half-2 chip at GW25.
    adv = _advice(
        [_surf(gw=25, tc_extra=10.0)],
        chips_used=["triple_captain@10"],
        current_gw=25,
    )["triple_captain"]
    assert adv.verdict == "advise"


def test_advise_only_current_half_gws_are_candidates():
    # current_gw=25 (half 2): a monster TC at GW10 (half 1) must be ignored.
    surface = [
        _surf(gw=10, tc_extra=15.0, tc_captain_dgw=True),
        _surf(gw=25, tc_extra=5.0),
    ]
    adv = _advice(surface, current_gw=25)["triple_captain"]
    assert adv.verdict == "hold"  # only the GW25 (5.0) candidate is in this half


def test_advise_empty_candidates_all_hold():
    # No surface GW in the current half and no change need → every chip holds.
    plan = _advice([_surf(gw=10)], current_gw=25, change_need=0)
    assert {a.verdict for a in plan.values()} == {"hold"}

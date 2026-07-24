"""Chip mechanics (Phase 3b) — offline, synthetic pool + a stub store.

Covers the four 2025/26 chips as wired into the backtest simulator:
bench_boost (all 15 score), triple_captain (captain x3), wildcard (unlimited
free transfers, kept), free_hit (unlimited free transfers, reverted).
"""

from __future__ import annotations

import pandas as pd
import pytest

from fpl_claude.backtest.simulate import (
    SquadState,
    canonical_chip,
    predicted_xi_breakdown,
    predicted_xi_points,
    score_gw,
    wildcard_squad,
)
from fpl_claude.optimize.milp import optimize
from fpl_claude.rules.engine import Ruleset


def _pool(gw_col: str = "xpts_gw1") -> pd.DataFrame:
    """6 clubs x (2 GKP, 3 DEF, 3 MID, 2 FWD) = 60 players, feasible under £100m."""
    rows = []
    pid = 0
    for t, team in enumerate(f"T{k}" for k in range(1, 7)):
        for position, count, base_price in (
            ("GKP", 2, 4.0), ("DEF", 3, 4.0), ("MID", 3, 5.0), ("FWD", 2, 5.5),
        ):
            for j in range(count):
                pid += 1
                score = pid / 10.0 + (10.0 if team == "T1" else 0.0)
                rows.append({
                    "id": pid, "web_name": f"{team}-{position}{j}", "team": team,
                    "position": position, "price": base_price + j * 0.5 + t * 0.2,
                    "xpts_horizon": round(score, 2), gw_col: round(score, 2),
                })
    return pd.DataFrame(rows)


class _StubStore:
    """Minimal SeasonStore stand-in: score_gw only calls actuals(gw)."""

    def __init__(self, points: dict[int, int], minutes: dict[int, int]):
        self._points, self._minutes = points, minutes

    def actuals(self, gw: int) -> pd.DataFrame:
        ids = list(self._points)
        return pd.DataFrame({
            "id": ids,
            "points": [self._points[i] for i in ids],
            "minutes": [self._minutes[i] for i in ids],
        })


@pytest.fixture(scope="module")
def rules() -> Ruleset:
    return Ruleset.load("2025-26")  # historical, verified — no allow_unverified needed


def test_canonical_chip_aliases_and_unknown():
    assert canonical_chip(None) is None
    assert canonical_chip("TC") == "triple_captain"
    assert canonical_chip("Bench Boost") == "bench_boost"
    assert canonical_chip("free-hit") == "free_hit"
    assert canonical_chip("wildcard") == "wildcard"
    with pytest.raises(ValueError, match="unknown chip"):
        canonical_chip("assistant_manager")  # not in the playable set here


def test_predicted_points_chip_variants(rules):
    pool = _pool()
    squad = optimize(pool, rules)
    by_id = pool.set_index("id")
    base = predicted_xi_points(squad, pool, 1)
    bb = predicted_xi_points(squad, pool, 1, chip="bench_boost")
    tc = predicted_xi_points(squad, pool, 1, chip="triple_captain")

    bench_pts = sum(float(by_id.loc[i, "xpts_gw1"]) for i in squad.bench)
    cap_pts = float(by_id.loc[squad.captain, "xpts_gw1"])
    assert bb == pytest.approx(base + bench_pts, abs=0.01)  # bench now counts
    assert tc == pytest.approx(base + cap_pts, abs=0.01)     # captain x3, not x2


def test_predicted_xi_breakdown_splits_base_and_captain(rules):
    """A2 calibration: the memo Outcome splits the predicted total into base XI
    (captain excluded) + the doubled/tripled captain slot. base + slot == total,
    and total is exactly what predicted_xi_points already returned."""
    pool = _pool()
    squad = optimize(pool, rules)
    by_id = pool.set_index("id")
    cap_xpts = float(by_id.loc[squad.captain, "xpts_gw1"])

    b = predicted_xi_breakdown(squad, pool, 1)
    # the split reconstructs the total, and the total is unchanged from before
    assert b.base_xi + b.captain_slot == pytest.approx(b.total, abs=0.01)
    assert b.total == predicted_xi_points(squad, pool, 1)
    # captain slot is the captain DOUBLED; base excludes the captain entirely
    assert b.captain_mult == 2
    assert b.captain_slot == pytest.approx(2 * cap_xpts, abs=0.01)
    base_manual = sum(float(by_id.loc[i, "xpts_gw1"]) for i in squad.xi if i != squad.captain)
    assert b.base_xi == pytest.approx(base_manual, abs=0.01)

    # triple captain: captain counts x3, the base XI is unchanged
    tc = predicted_xi_breakdown(squad, pool, 1, chip="triple_captain")
    assert tc.captain_mult == 3
    assert tc.captain_slot == pytest.approx(3 * cap_xpts, abs=0.01)
    assert tc.base_xi == pytest.approx(base_manual, abs=0.01)
    assert tc.total == predicted_xi_points(squad, pool, 1, chip="triple_captain")

    # bench boost: the base spans all 14 non-captain squad players, captain still x2
    bb = predicted_xi_breakdown(squad, pool, 1, chip="bench_boost")
    assert bb.captain_mult == 2
    base_bb = sum(float(by_id.loc[i, "xpts_gw1"]) for i in squad.squad if i != squad.captain)
    assert bb.base_xi == pytest.approx(base_bb, abs=0.01)
    assert bb.base_xi + bb.captain_slot == pytest.approx(bb.total, abs=0.01)
    assert bb.total == predicted_xi_points(squad, pool, 1, chip="bench_boost")


def test_score_gw_bench_boost_counts_all_fifteen(rules):
    pool = _pool()
    squad = optimize(pool, rules)
    points = {i: 2 for i in squad.squad}
    points[squad.captain] = 9
    minutes = {i: 90 for i in squad.squad}  # everyone plays: no autosubs
    store = _StubStore(points, minutes)

    normal, _, _, _ = score_gw(store, 1, squad, pool, rules)
    boosted, _, _, _ = score_gw(store, 1, squad, pool, rules, chip="bench_boost")
    # Bench boost adds exactly the four bench players' points (each 2 here).
    assert boosted - normal == sum(points[i] for i in squad.bench) == 8


def test_score_gw_triple_captain_adds_one_more_captain(rules):
    pool = _pool()
    squad = optimize(pool, rules)
    points = {i: 2 for i in squad.squad}
    points[squad.captain] = 10
    minutes = {i: 90 for i in squad.squad}
    store = _StubStore(points, minutes)

    normal, _, _, _ = score_gw(store, 1, squad, pool, rules)
    tripled, _, _, _ = score_gw(store, 1, squad, pool, rules, chip="triple_captain")
    assert tripled - normal == points[squad.captain] == 10  # one extra captain haul


def _worst_squad_state(pool: pd.DataFrame) -> SquadState:
    """Own the 15 lowest scorers (max 3/club) with plenty of bank."""
    counts = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    club: dict[str, int] = {}
    ids: list[int] = []
    for _, r in pool.sort_values("xpts_horizon").iterrows():
        if counts.get(r["position"], 0) > 0 and club.get(r["team"], 0) < 3:
            ids.append(int(r["id"]))
            counts[r["position"]] -= 1
            club[r["team"]] = club.get(r["team"], 0) + 1
        if len(ids) == 15:
            break
    by_id = pool.set_index("id")
    return SquadState(
        buy_costs={i: int(round(by_id.loc[i, "price"] * 10)) for i in ids},
        bank=200, free_transfers=1,
    )


def test_wildcard_squad_is_unlimited_and_free(rules):
    pool = _pool()
    state = _worst_squad_state(pool)
    wc = wildcard_squad(pool, rules, state)
    assert wc.hits == 0  # every transfer is free on a wildcard
    # It should reshape more than the single free transfer a normal solve allows.
    assert len(wc.transfers_in) >= 2


def test_chip_one_per_half_enforced():
    state = SquadState(buy_costs={}, bank=0, free_transfers=1,
                       chips_used=["triple_captain@5"])
    from fpl_claude.backtest.simulate import _assert_chip_available
    # Same chip, same half (GW1-19) -> blocked.
    with pytest.raises(ValueError, match="already used"):
        _assert_chip_available("triple_captain", 12, state)
    # Same chip, second half (GW20+) -> allowed (fresh set).
    _assert_chip_available("triple_captain", 25, state)
    # A different chip in the same half -> allowed.
    _assert_chip_available("bench_boost", 12, state)

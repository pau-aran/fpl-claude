"""MILP optimizer tests — synthetic projections, offline, HiGHS or CBC."""

from __future__ import annotations

import pandas as pd
import pytest

from fpl_claude.optimize.milp import (
    CurrentSquad,
    RulesetUnverifiedError,
    optimize,
)
from fpl_claude.rules.engine import Ruleset


def _pool() -> pd.DataFrame:
    """6 clubs x (2 GKP, 3 DEF, 3 MID, 2 FWD) = 60 players, feasible under £100m.

    Scores rise with player index so optima are deterministic; club T1 is
    deliberately stacked to exercise the 3-per-club cap.
    """
    rows = []
    pid = 0
    for t, team in enumerate(f"T{k}" for k in range(1, 7)):
        for position, count, base_price in (
            ("GKP", 2, 4.0), ("DEF", 3, 4.0), ("MID", 3, 5.0), ("FWD", 2, 5.5),
        ):
            for j in range(count):
                pid += 1
                score = pid / 10.0 + (10.0 if team == "T1" else 0.0)
                rows.append(
                    {
                        "id": pid,
                        "web_name": f"{team}-{position}{j}",
                        "team": team,
                        "position": position,
                        "price": base_price + j * 0.5 + t * 0.2,
                        "xpts_horizon": round(score, 2),
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def rules() -> Ruleset:
    return Ruleset.load("2026-27")


@pytest.fixture(scope="module")
def pool() -> pd.DataFrame:
    return _pool()


def test_refuses_unverified_ruleset(pool, rules):
    assert not rules.is_verified()  # 2026/27 not verified until season launch
    with pytest.raises(RulesetUnverifiedError, match="unverified"):
        optimize(pool, rules)


def test_initial_build_respects_all_constraints(pool, rules):
    result = optimize(pool, rules, allow_unverified=True)
    by_id = pool.set_index("id")
    squad = by_id.loc[result.squad]

    assert len(result.squad) == 15 and len(result.xi) == 11 and len(result.bench) == 4
    assert squad["position"].value_counts().to_dict() == {
        "DEF": 5, "MID": 5, "GKP": 2, "FWD": 3,
    }
    assert squad["team"].value_counts().max() <= 3  # T1 is stacked; cap must bind
    assert squad["team"].value_counts()["T1"] == 3
    assert result.cost <= 1000  # tenths

    xi = by_id.loc[result.xi]
    counts = xi["position"].value_counts()
    assert counts["GKP"] == 1
    assert counts["DEF"] >= 3 and counts["MID"] >= 2 and counts["FWD"] >= 1

    # Captain is the best XI scorer, vice the runner-up, both in the XI.
    xi_sorted = xi.sort_values("xpts_horizon", ascending=False)
    assert result.captain == xi_sorted.index[0]
    assert result.vice == xi_sorted.index[1]
    # Bench: outfielders by descending score, keeper last.
    assert by_id.loc[result.bench[-1], "position"] == "GKP"
    outfield_scores = [by_id.loc[i, "xpts_horizon"] for i in result.bench[:-1]]
    assert outfield_scores == sorted(outfield_scores, reverse=True)


def test_budget_binds():
    """With a tight budget the optimizer prefers value, not just raw points."""
    pool = _pool()
    rules = Ruleset.load("2026-27")
    tight = Ruleset({**rules.raw, "budget": {**rules.raw["budget"], "initial": 78.0}})
    result = optimize(pool, tight, allow_unverified=True)
    assert result.cost <= 780
    full = optimize(pool, rules, allow_unverified=True)
    assert result.objective <= full.objective


def test_transfer_mode_takes_profitable_swap(pool, rules):
    """Own the worst legal squad -> one free transfer buys the biggest upgrade."""
    by_score = pool.sort_values("xpts_horizon")
    squad_ids: list[int] = []
    counts = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    club_count: dict[str, int] = {}
    for _, row in by_score.iterrows():
        if counts.get(row["position"], 0) > 0 and club_count.get(row["team"], 0) < 3:
            squad_ids.append(row["id"])
            counts[row["position"]] -= 1
            club_count[row["team"]] = club_count.get(row["team"], 0) + 1
        if len(squad_ids) == 15:
            break
    current = CurrentSquad(
        buy_costs={i: int(pool.set_index("id").loc[i, "price"] * 10) for i in squad_ids},
        bank=100,  # £10m in the bank: upgrades are affordable
        free_transfers=1,
    )

    free_only = optimize(
        pool, rules, current=current, max_transfers=1, allow_unverified=True
    )
    assert len(free_only.transfers_in) == 1 and len(free_only.transfers_out) == 1
    assert free_only.hits == 0
    assert free_only.ev_delta is not None and free_only.ev_delta > 0

    unlimited = optimize(pool, rules, current=current, allow_unverified=True)
    assert len(unlimited.transfers_in) >= 1
    # Hits charged beyond the single free transfer:
    assert unlimited.hits == max(0, len(unlimited.transfers_in) - 1)
    # Extra hits were only taken because they pay for themselves:
    assert unlimited.ev_delta >= free_only.ev_delta


def test_transfer_mode_no_move_when_gain_below_hit(rules):
    """Marginal upgrades that don't cover a -4 are refused once frees are spent."""
    rows = []
    for k in range(15):
        position = ["GKP", "GKP", "DEF", "DEF", "DEF", "DEF", "DEF",
                    "MID", "MID", "MID", "MID", "MID", "FWD", "FWD", "FWD"][k]
        rows.append({"id": k + 1, "web_name": f"own{k}", "team": f"T{k % 5}",
                     "position": position, "price": 5.0, "xpts_horizon": 20.0})
    # One outside option: +1 pt over the weakest starter — under the 4-pt hit.
    rows.append({"id": 99, "web_name": "meh", "team": "T9", "position": "MID",
                 "price": 5.0, "xpts_horizon": 21.0})
    pool = pd.DataFrame(rows)
    current = CurrentSquad(
        buy_costs={k + 1: 50 for k in range(15)}, bank=0, free_transfers=0
    )
    result = optimize(pool, rules, current=current, allow_unverified=True)
    assert result.transfers_in == [] and result.hits == 0
    assert result.ev_delta == pytest.approx(0.0, abs=0.01)


def test_owned_player_missing_from_projections_raises(pool, rules):
    current = CurrentSquad(buy_costs={9999: 50}, bank=0, free_transfers=1)
    with pytest.raises(ValueError, match="9999"):
        optimize(pool, rules, current=current, allow_unverified=True)

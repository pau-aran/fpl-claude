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


def test_manager_lock_and_ban(pool, rules):
    """The human layer can pin players in or out of the solve (rule 4)."""
    base = optimize(pool, rules, allow_unverified=True)
    outside = next(i for i in pool["id"] if i not in base.squad)
    star = base.squad[0]

    locked = optimize(pool, rules, allow_unverified=True, lock=frozenset({outside}))
    assert outside in locked.squad
    banned = optimize(pool, rules, allow_unverified=True, ban=frozenset({star}))
    assert star not in banned.squad
    # Constrained solves can never beat the free optimum.
    assert locked.objective <= base.objective
    assert banned.objective <= base.objective


def test_marginal_hit_gate_rejects_piggyback_hit(rules):
    """A hit must clear the EV threshold ON ITS OWN, not ride in on a big
    free move's package delta (backtest GW2 review finding)."""
    from fpl_claude.backtest.simulate import SquadState, decide_transfers

    rows = []
    for k in range(15):
        position = ["GKP", "GKP", "DEF", "DEF", "DEF", "DEF", "DEF",
                    "MID", "MID", "MID", "MID", "MID", "FWD", "FWD", "FWD"][k]
        rows.append({"id": k + 1, "web_name": f"own{k}", "team": f"T{k % 5}",
                     "position": position, "price": 5.0, "xpts_horizon": 20.0,
                     "xpts_gw2": 4.0})
    # Big free upgrade (+15 over an owned MID) and a small extra (+4.1 over
    # an owned FWD): the +4.1 clears the solver's -4 hit cost (package-positive,
    # so the optimizer takes it) but nets only ~+0.1 — far below the required
    # NET hit_ev_threshold (4.5) per hit. The gate must strip it while keeping
    # the free move.
    rows.append({"id": 98, "web_name": "big", "team": "T8", "position": "MID",
                 "price": 5.0, "xpts_horizon": 35.0, "xpts_gw2": 8.0})
    rows.append({"id": 99, "web_name": "small", "team": "T9", "position": "FWD",
                 "price": 5.0, "xpts_horizon": 24.1, "xpts_gw2": 5.0})
    pool2 = pd.DataFrame(rows)
    state = SquadState(
        buy_costs={k + 1: 50 for k in range(15)}, bank=0, free_transfers=1
    )
    verified = Ruleset({**rules.raw, "verified_against_official": True})
    for section in verified.raw.values():
        if isinstance(section, dict):
            section.pop("verify_at_season_launch", None)
    result, audit = decide_transfers(pool2, verified, state)
    assert 98 in result.transfers_in  # the free move stands
    assert 99 not in result.transfers_in  # the piggyback hit is refused
    assert result.hits == 0
    assert audit["hit_gate"].startswith("rejected")


def test_marginal_hit_gate_keeps_hit_that_nets_threshold(rules):
    """A hit whose NET marginal gain (after the -4) clears the threshold stays."""
    from fpl_claude.backtest.simulate import SquadState, decide_transfers

    rows = []
    for k in range(15):
        position = ["GKP", "GKP", "DEF", "DEF", "DEF", "DEF", "DEF",
                    "MID", "MID", "MID", "MID", "MID", "FWD", "FWD", "FWD"][k]
        rows.append({"id": k + 1, "web_name": f"own{k}", "team": f"T{k % 5}",
                     "position": position, "price": 5.0, "xpts_horizon": 20.0,
                     "xpts_gw2": 4.0})
    rows.append({"id": 98, "web_name": "big", "team": "T8", "position": "MID",
                 "price": 5.0, "xpts_horizon": 35.0, "xpts_gw2": 8.0})
    # +10 gross over an owned FWD -> net +6 after the -4: clears 4.5/hit.
    rows.append({"id": 99, "web_name": "worth-it", "team": "T9", "position": "FWD",
                 "price": 5.0, "xpts_horizon": 30.0, "xpts_gw2": 7.0})
    pool2 = pd.DataFrame(rows)
    state = SquadState(
        buy_costs={k + 1: 50 for k in range(15)}, bank=0, free_transfers=1
    )
    verified = Ruleset({**rules.raw, "verified_against_official": True})
    for section in verified.raw.values():
        if isinstance(section, dict):
            section.pop("verify_at_season_launch", None)
    result, audit = decide_transfers(pool2, verified, state)
    assert 98 in result.transfers_in and 99 in result.transfers_in
    assert result.hits == 1
    assert audit["hit_gate"].startswith("kept")


def test_reselect_xi_benches_high_horizon_blank_for_soft_fixture(rules):
    """The bench-order fix: a high-horizon player who blanks THIS week (e.g. a
    suspension) must be benched in favour of a lower-horizon player with a better
    current-GW fixture. Squad membership is untouched — only the XI split changes."""
    from fpl_claude.backtest.simulate import reselect_xi
    from fpl_claude.optimize.milp import OptimizedSquad

    # 15-man squad: 2 GKP, 5 DEF, 5 MID, 3 FWD. One MID ("banned") has the best
    # horizon but ~0 this GW; a bench MID ("soft") has a lower horizon but a strong
    # current-GW score and should be started over him.
    rows = []
    specs = [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]
    pid = 0
    for position, count in specs:
        for _ in range(count):
            pid += 1
            rows.append({"id": pid, "web_name": f"p{pid}", "team": f"T{pid % 6}",
                         "position": position, "price": 5.0,
                         "xpts_horizon": 10.0, "xpts_gw7": 4.0})
    df = pd.DataFrame(rows)
    banned = 8  # a MID (ids 8-12 are MID); top horizon, blanks this week
    soft = 12   # a MID; lower horizon, best current-GW fixture
    df.loc[df["id"] == banned, ["xpts_horizon", "xpts_gw7"]] = [30.0, 0.1]
    df.loc[df["id"] == soft, ["xpts_horizon", "xpts_gw7"]] = [9.0, 7.5]

    squad = OptimizedSquad(
        squad=list(range(1, 16)), xi=list(range(1, 12)),
        captain=banned, vice=1, bench=[12, 13, 14, 15],
        cost=750, objective=0.0,
    )
    fixed = reselect_xi(squad, df, rules, gw=7)
    assert banned not in fixed.xi and banned in fixed.bench  # blank benched
    assert soft in fixed.xi                                  # soft fixture started
    assert fixed.captain == soft                             # captain = top this-GW
    assert set(fixed.squad) == set(range(1, 16))             # membership unchanged

"""Multi-period transfer PATH planner — offline, synthetic per-GW projections.

Covers the behaviour A4 exists for: valuing a BANKED free transfer for what it
unlocks later (the returnee-window case), the free-transfer banking cap binding,
hits being charged AND gated at the rules threshold, graceful degradation to a
single-period answer, and pool pruning never dropping a player we own.

Everything is built from synthetic frames — no network, no db/.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fpl_claude.optimize.milp import CurrentSquad, RulesetUnverifiedError
from fpl_claude.optimize.transfer_path import (
    MAX_PLANNING_GWS,
    POOL_TOP_N_PER_POSITION,
    horizon_columns,
    plan_transfer_path,
    prune_pool,
)
from fpl_claude.rules.engine import Ruleset

GWS = (1, 2, 3)
OWNED_SHAPE = ["GKP"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3


@pytest.fixture(scope="module")
def rules() -> Ruleset:
    return Ruleset.load("2026-27")


def _row(pid: int, name: str, position: str, team: str, scores, price: float = 5.0) -> dict:
    """One projections row: a flat `price` plus one xpts column per horizon GW."""
    row = {
        "id": pid,
        "web_name": name,
        "team": team,
        "position": position,
        "price": price,
        "xpts_horizon": round(sum(scores), 2),
    }
    row.update({f"xpts_gw{gw}": float(s) for gw, s in zip(GWS, scores)})
    return row


def _owned_rows(
    overrides: dict[int, list[float]] | None = None,
    prices: dict[int, float] | None = None,
) -> list[dict]:
    """A legal owned 15 (2/5/5/3) across five clubs — exactly at the 3-per-club
    cap, so every BUY has to come from a different club. Flat 2.0 every GW at
    £5.0m unless `overrides`/`prices` give a player his own line."""
    overrides = overrides or {}
    prices = prices or {}
    rows = []
    for k, position in enumerate(OWNED_SHAPE):
        pid = k + 1
        rows.append(
            _row(pid, f"own{pid}", position, f"C{k % 5}",
                 overrides.get(pid, [2.0] * len(GWS)), prices.get(pid, 5.0))
        )
    return rows


def _current(rows: list[dict], free_transfers: int, bank: int = 0) -> CurrentSquad:
    """Own everything in `rows` whose id is inside the squad-15 range, at its
    listed price (so sell_price() returns that price back — no profit modelled)."""
    return CurrentSquad(
        buy_costs={
            int(r["id"]): round(float(r["price"]) * 10)
            for r in rows
            if int(r["id"]) <= len(OWNED_SHAPE)
        },
        bank=bank,
        free_transfers=free_transfers,
    )


# ------------------------------------------------------- the A4 headline case


def test_banking_beats_spending_when_the_window_is_later(rules):
    """The returnee window, in miniature (the GW17-24 shape made model-derived).

    Two owned premiums are good THIS week and worthless from GW2; the two
    returnees who replace them are worthless this week and strong from GW2. Bank
    is £0 and the returnees are premium-priced, so the ONLY funding route is
    selling those two — buying either returnee early therefore throws away this
    week's points. One free transfer cannot make both swaps, so the planner must
    ROLL, bank to 2 FT, and queue BOTH moves for GW2.
    """
    rows = _owned_rows(
        {8: [8.0, 0.0, 0.0], 13: [8.0, 0.0, 0.0]},  # a MID and a FWD
        {8: 10.0, 13: 10.0},  # ...who are also the only funding for the returnees
    )
    rows += [
        _row(90, "retMID", "MID", "X0", [0.0, 8.0, 8.0], price=10.0),
        _row(91, "retFWD", "FWD", "X1", [0.0, 8.0, 8.0], price=10.0),
        _row(92, "smallMID", "MID", "X2", [2.5, 2.5, 2.5]),  # the tempting move-now
    ]
    path = plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=1), allow_unverified=True
    )

    assert path.verdict == "roll" and path.this_week.is_roll
    assert path.roll_gain is not None and path.roll_gain > 0  # banking is worth points
    assert path.decisive
    # Banked: 1 FT this week becomes 2 next week, and both moves land free at GW2.
    assert path.this_week.free_transfers_after == 1
    assert path.forward[0].free_transfers_before == 2
    gw2 = next(m for m in path.forward_moves if m.gw == 2)
    assert set(gw2.in_ids) == {90, 91} and set(gw2.out_ids) == {8, 13}
    assert gw2.hits == 0
    assert "ROLL" in path.rationale and "GW2" in path.rationale


def test_banking_cap_binds(rules):
    """Free transfers accumulate at `transfers.free_per_gameweek` but never past
    `transfers.max_banked` — start at the cap and it must stay there, not grow."""
    cap = int(rules.raw["transfers"]["max_banked"])
    rows = _owned_rows()
    path = plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=cap),
        allow_unverified=True,
    )
    trajectory = [m.free_transfers_before for m in (path.this_week, *path.forward)]
    assert trajectory == [cap] * len(GWS)  # pinned at the cap, never cap + 1


def test_free_transfers_are_capped_on_entry(rules):
    """A state carrying more FTs than the rules allow is clamped, not trusted."""
    cap = int(rules.raw["transfers"]["max_banked"])
    rows = _owned_rows()
    path = plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=cap + 3),
        allow_unverified=True,
    )
    assert path.this_week.free_transfers_before == cap


# ------------------------------------------------------------------ hit gating


def _hit_case(rules, target_scores: list[float]):
    rows = _owned_rows() + [_row(90, "target", "MID", "X0", target_scores)]
    return plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=0), allow_unverified=True
    )


def test_hit_is_charged_and_kept_when_it_clears_the_threshold(rules):
    """0 FT + a huge immediate upgrade: the -4 is charged and the gate keeps it."""
    path = _hit_case(rules, [20.0, 20.0, 20.0])
    assert path.this_week.hits == 1
    assert 90 in path.this_week.in_ids
    assert path.hit_gate.startswith("kept")


def test_hit_below_threshold_is_stripped_and_the_move_deferred(rules):
    """The same shape with a modest upgrade: taking the hit is package-positive
    (+6 gross vs the -4) but nets only ~+2, under policies.hit_ev_threshold. The
    gate strips it — and the multi-period model does the useful thing with the
    refusal, deferring the move to next week's FREE transfer."""
    path = _hit_case(rules, [5.0, 5.0, 5.0])
    assert path.this_week.hits == 0
    assert path.hit_gate.startswith("rejected")
    assert any(90 in m.in_ids for m in path.forward_moves)


# ----------------------------------------------------------- degradation paths


def _single_column(rows: list[dict]) -> list[dict]:
    """Strip every per-GW column except xpts_gw1 (the one-column degradation)."""
    return [
        {k: v for k, v in r.items() if not k.startswith("xpts_gw") or k == "xpts_gw1"}
        for r in rows
    ]


def test_single_gw_column_degrades_to_a_single_period(rules):
    """One per-GW column must yield a sane one-week answer, not a crash."""
    rows = _single_column(_owned_rows() + [_row(90, "up", "MID", "X0", [9.0, 0.0, 0.0])])
    path = plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=1), allow_unverified=True
    )
    assert path.horizon_gws == 1 and path.gws == (1,)
    assert path.forward == ()
    assert path.verdict == "move" and 90 in path.this_week.in_ids
    assert any("single-period" in c for c in path.caveats)


def test_horizon_columns_truncate_and_fall_back():
    frame = pd.DataFrame(
        [{"id": 1, "price": 5.0, "position": "MID", "team": "A",
          **{f"xpts_gw{g}": 1.0 for g in range(1, 9)}}]
    )
    assert horizon_columns(frame) == [(g, f"xpts_gw{g}") for g in range(1, MAX_PLANNING_GWS + 1)]
    assert horizon_columns(frame, horizon=2) == [(1, "xpts_gw1"), (2, "xpts_gw2")]
    # No per-GW columns at all -> a single xpts_horizon pseudo-period, no raise.
    assert horizon_columns(pd.DataFrame([{"id": 1, "xpts_horizon": 3.0}])) == [
        (0, "xpts_horizon")
    ]


# ------------------------------------------------------------- pool pruning


def test_prune_pool_keeps_owned_and_locked():
    """Pruning is what makes the model tractable — it must never drop a player we
    own (rolling the current squad has to stay feasible) or one the manager locked."""
    rows = []
    pid = 0
    for position in ("GKP", "DEF", "MID", "FWD"):
        for k in range(80):
            pid += 1
            rows.append(_row(pid, f"p{pid}", position, f"C{pid % 20}", [0.01 * k] * len(GWS)))
    frame = pd.DataFrame(rows)
    owned = {1, 2, 3, 81, 82, 161, 162, 241}  # deliberately the WORST scorers
    locked = frozenset({4})
    pool = prune_pool(frame, owned, keep=locked)

    assert owned <= set(pool["id"])
    assert 4 in set(pool["id"])
    assert len(pool) < len(frame)
    for position in ("GKP", "DEF", "MID", "FWD"):
        block = pool[pool["position"] == position]
        assert len(block) >= POOL_TOP_N_PER_POSITION


# ---------------------------------------------------------------- guardrails


def test_refuses_unverified_ruleset(rules):
    assert not rules.is_verified()
    rows = _owned_rows()
    with pytest.raises(RulesetUnverifiedError, match="unverified"):
        plan_transfer_path(pd.DataFrame(rows), rules, _current(rows, 1))


def test_owned_player_missing_from_projections_raises(rules):
    current = CurrentSquad(buy_costs={9999: 50}, bank=0, free_transfers=1)
    with pytest.raises(ValueError, match="9999"):
        plan_transfer_path(
            pd.DataFrame(_owned_rows()), rules, current, allow_unverified=True
        )


def test_manager_ban_is_honoured_across_the_whole_path(rules):
    """A banned player must not appear anywhere in the path, not merely this week."""
    rows = _owned_rows({8: [8.0, 0.0, 0.0]})
    rows += [_row(90, "banned", "MID", "X0", [0.0, 9.0, 9.0])]
    path = plan_transfer_path(
        pd.DataFrame(rows), rules, _current(rows, free_transfers=1),
        allow_unverified=True, ban=frozenset({90}),
    )
    assert all(90 not in m.in_ids for m in (path.this_week, *path.forward))

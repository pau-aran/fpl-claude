"""MILP squad optimizer — PuLP + HiGHS (CBC fallback), open-fpl-solver formulation.

Selects squad-15, XI, captain, vice, bench order — and in transfer mode, who to
buy/sell with hit accounting — maximizing decayed-horizon expected points from
the projections table (models/projections.py). Every constraint value comes from
the rules engine, never hard-coded.

The optimizer REFUSES to run while the ruleset has unverified sections
(config/rules/*.yaml, verify_at_season_launch) unless explicitly overridden —
pre-season dry runs pass allow_unverified=True and label output accordingly.

The result is a CANDIDATE, not an order (CLAUDE.md rule 4): the decision memo
overlays what models can't see, and deviations are written down. ev_delta (vs
rolling the squad unchanged) is what memos quote against policies.hit_ev_threshold.

v1 scope: single-period over the decayed horizon score (xpts_horizon). The
multi-period transfer path and chip planning build on this in Phase 3b.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pulp

from ..rules.engine import Ruleset

BENCH_WEIGHT = 0.10  # bench points count ~10%: autosub value without XI distortion
VICE_WEIGHT = 0.05  # tiny pull toward a strong vice, never at XI's expense

POSITIONS = ("GKP", "DEF", "MID", "FWD")


class RulesetUnverifiedError(RuntimeError):
    """Raised when optimizing against a ruleset not yet verified vs the official site."""


class InfeasibleError(RuntimeError):
    """Raised when the model has no feasible solution (bad inputs, over-constrained)."""


@dataclass(frozen=True)
class CurrentSquad:
    """What we own: player id -> buy cost (API tenths), bank (tenths), free transfers."""

    buy_costs: dict[int, int]
    bank: int
    free_transfers: int


@dataclass(frozen=True)
class OptimizedSquad:
    squad: list[int]
    xi: list[int]
    captain: int
    vice: int
    bench: list[int]  # order: outfield by descending score, keeper last
    cost: int  # squad purchase cost in tenths (transfer mode: spend on buys)
    objective: float
    transfers_in: list[int] = field(default_factory=list)
    transfers_out: list[int] = field(default_factory=list)
    hits: int = 0
    ev_delta: float | None = None  # objective gain vs no-transfer baseline


def _solver() -> pulp.LpSolver:
    try:
        solver = pulp.HiGHS(msg=False)
        if solver.available():
            return solver
    except Exception:  # noqa: BLE001 — any HiGHS wiring issue means fall back
        pass
    return pulp.PULP_CBC_CMD(msg=0)


def _check_columns(projections: pd.DataFrame, score_col: str) -> None:
    required = {"id", "position", "team", "price", score_col}
    missing = required - set(projections.columns)
    if missing:
        raise ValueError(f"projections table missing columns: {sorted(missing)}")


def _solve(
    players: pd.DataFrame,
    rules: Ruleset,
    score_col: str,
    current: CurrentSquad | None,
    max_transfers: int | None,
) -> OptimizedSquad:
    shape = rules.squad_shape()
    lineup = rules.raw["lineup"]
    max_per_club = int(rules.raw["squad"]["max_per_club"])
    budget = int(rules.raw["budget"]["initial"] * 10)
    hit_cost = float(rules.raw["transfers"]["hit_cost"])

    ids = list(players["id"])
    by_id = players.set_index("id")
    price = {i: int(round(by_id.loc[i, "price"] * 10)) for i in ids}
    score = {i: float(by_id.loc[i, score_col]) for i in ids}
    pos = {i: by_id.loc[i, "position"] for i in ids}
    club = {i: by_id.loc[i, "team"] for i in ids}

    prob = pulp.LpProblem("fpl_squad", pulp.LpMaximize)
    s = prob.add_variable_dicts("squad", ids, cat="Binary")
    x = prob.add_variable_dicts("xi", ids, cat="Binary")
    c = prob.add_variable_dicts("captain", ids, cat="Binary")
    v = prob.add_variable_dicts("vice", ids, cat="Binary")

    # Squad shape and club limit
    prob += pulp.lpSum(s[i] for i in ids) == sum(shape.values())
    for p in POSITIONS:
        prob += pulp.lpSum(s[i] for i in ids if pos[i] == p) == shape[p]
    for team in set(club.values()):
        prob += pulp.lpSum(s[i] for i in ids if club[i] == team) <= max_per_club

    # XI formation (exact keepers; positional minimums per rules)
    prob += pulp.lpSum(x[i] for i in ids) == int(lineup["starting"])
    prob += pulp.lpSum(x[i] for i in ids if pos[i] == "GKP") == int(lineup["min_goalkeepers"])
    prob += pulp.lpSum(x[i] for i in ids if pos[i] == "DEF") >= int(lineup["min_defenders"])
    prob += pulp.lpSum(x[i] for i in ids if pos[i] == "MID") >= int(lineup["min_midfielders"])
    prob += pulp.lpSum(x[i] for i in ids if pos[i] == "FWD") >= int(lineup["min_forwards"])

    # Captain and vice: one each, distinct, from the XI
    prob += pulp.lpSum(c[i] for i in ids) == 1
    prob += pulp.lpSum(v[i] for i in ids) == 1
    for i in ids:
        prob += x[i] <= s[i]
        prob += c[i] <= x[i]
        prob += v[i] <= x[i]
        prob += c[i] + v[i] <= 1

    hits = None
    if current is None:
        prob += pulp.lpSum(s[i] * price[i] for i in ids) <= budget
    else:
        owned = [i for i in current.buy_costs if i in by_id.index]
        bought = [i for i in ids if i not in current.buy_costs]
        sell = {i: rules.sell_price(current.buy_costs[i], price[i]) for i in owned}
        # Spend on buys must fit bank + proceeds of sales
        prob += pulp.lpSum(s[i] * price[i] for i in bought) <= current.bank + pulp.lpSum(
            (1 - s[i]) * sell[i] for i in owned
        )
        n_transfers = pulp.lpSum(s[i] for i in bought)
        if max_transfers is not None:
            prob += n_transfers <= max_transfers
        hits = prob.add_variable("hits", lowBound=0, cat="Integer")
        prob += hits >= n_transfers - current.free_transfers

    objective = (
        pulp.lpSum(x[i] * score[i] for i in ids)
        + pulp.lpSum(c[i] * score[i] for i in ids)
        + VICE_WEIGHT * pulp.lpSum(v[i] * score[i] for i in ids)
        + BENCH_WEIGHT * pulp.lpSum((s[i] - x[i]) * score[i] for i in ids)
    )
    if hits is not None:
        objective -= hit_cost * hits
    prob += objective

    status = prob.solve(_solver())
    if pulp.LpStatus[status] != "Optimal":
        raise InfeasibleError(f"solver status: {pulp.LpStatus[status]}")

    chosen = [i for i in ids if s[i].value() > 0.5]
    xi = [i for i in chosen if x[i].value() > 0.5]
    bench_ids = [i for i in chosen if i not in xi]
    bench = sorted(
        (i for i in bench_ids if pos[i] != "GKP"), key=lambda i: -score[i]
    ) + [i for i in bench_ids if pos[i] == "GKP"]

    transfers_in: list[int] = []
    transfers_out: list[int] = []
    if current is not None:
        transfers_in = [i for i in chosen if i not in current.buy_costs]
        transfers_out = [i for i in current.buy_costs if i not in chosen]
        cost = sum(price[i] for i in transfers_in)
    else:
        cost = sum(price[i] for i in chosen)

    return OptimizedSquad(
        squad=sorted(chosen, key=lambda i: (POSITIONS.index(pos[i]), -score[i])),
        xi=sorted(xi, key=lambda i: (POSITIONS.index(pos[i]), -score[i])),
        captain=next(i for i in ids if c[i].value() > 0.5),
        vice=next(i for i in ids if v[i].value() > 0.5),
        bench=bench,
        cost=cost,
        objective=round(pulp.value(prob.objective), 3),
        transfers_in=sorted(transfers_in),
        transfers_out=sorted(transfers_out),
        hits=int(hits.value()) if hits is not None else 0,
    )


def optimize(
    projections: pd.DataFrame,
    rules: Ruleset | None = None,
    current: CurrentSquad | None = None,
    max_transfers: int | None = None,
    score_col: str = "xpts_horizon",
    allow_unverified: bool = False,
) -> OptimizedSquad:
    """Optimal squad from a projections table.

    current=None: initial build (GW1 / wildcard) within the rules budget.
    current given: transfer mode — buys/sells priced at sell_price(), hits
    charged beyond free transfers, and ev_delta populated with the objective
    gain over rolling the current squad unchanged (memos quote this against
    policies.hit_ev_threshold).
    """
    rules = rules or Ruleset.load()
    if not rules.is_verified() and not allow_unverified:
        raise RulesetUnverifiedError(
            "ruleset has unverified sections "
            f"{rules.unverified_sections()} — verify vs the official site at season "
            "launch, or pass allow_unverified=True for a dry run and label the output"
        )
    _check_columns(projections, score_col)
    players = projections.drop_duplicates(subset="id")
    if current is not None:
        missing = set(current.buy_costs) - set(players["id"])
        if missing:
            raise ValueError(
                f"owned players missing from projections table: {sorted(missing)}"
            )

    result = _solve(players, rules, score_col, current, max_transfers)
    if current is not None:
        baseline = _solve(players, rules, score_col, current, max_transfers=0)
        result = OptimizedSquad(
            **{
                **result.__dict__,
                "ev_delta": round(result.objective - baseline.objective, 3),
            }
        )
    return result

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

import re
from dataclasses import dataclass, field

import pandas as pd
import pulp

from ..rules.engine import Ruleset

_GW_COL = re.compile(r"xpts_gw(\d+)$")

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


def _pick_lineup(
    squad_ids: list[int],
    score: dict[int, float],
    pos: dict[int, str],
    lineup: dict,
    force_start: frozenset[int] = frozenset(),
    force_bench: frozenset[int] = frozenset(),
) -> tuple[list[int], int, int, list[int]]:
    """Pick the best legal starting XI, captain, vice and bench order for ONE
    gameweek from an already-chosen squad-15, using a single-GW `score`.

    Owning the 15 is a horizon question (the MILP); who STARTS this week is a
    single-fixture question — conflating them benched a soft-fixture defender
    behind a hard-fixture one (backtest GW10). Captain/vice and bench order use
    the true `score`; `force_start`/`force_bench` are the manager overlay (a
    depleted-defence read the stats model can't see, backtest GW13).
    """
    big = 1e6

    def rank(i: int) -> float:
        return score[i] + (big if i in force_start else 0.0) - (
            big if i in force_bench else 0.0
        )

    keepers = sorted((i for i in squad_ids if pos[i] == "GKP"), key=lambda i: -rank(i))
    defs = sorted((i for i in squad_ids if pos[i] == "DEF"), key=lambda i: -rank(i))
    mids = sorted((i for i in squad_ids if pos[i] == "MID"), key=lambda i: -rank(i))
    fwds = sorted((i for i in squad_ids if pos[i] == "FWD"), key=lambda i: -rank(i))
    min_def = int(lineup["min_defenders"])
    min_mid = int(lineup["min_midfielders"])
    min_fwd = int(lineup["min_forwards"])
    n_out = int(lineup["starting"]) - int(lineup["min_goalkeepers"])

    best: tuple[float, list[int]] | None = None
    for d in range(min_def, len(defs) + 1):
        for m in range(min_mid, len(mids) + 1):
            f = n_out - d - m
            if f < min_fwd or f > len(fwds):
                continue
            picked = defs[:d] + mids[:m] + fwds[:f]
            total = rank(keepers[0]) + sum(rank(i) for i in picked)
            if best is None or total > best[0]:
                best = (total, picked)
    assert best is not None  # a legal formation always exists for a valid squad
    picked = best[1]
    xi = [keepers[0]] + picked
    xi_set = set(xi)
    ranked = sorted(xi, key=lambda i: -score[i])  # captain on TRUE single-GW score
    captain, vice = ranked[0], ranked[1]
    bench = sorted(
        (i for i in defs + mids + fwds if i not in xi_set), key=lambda i: -score[i]
    ) + [keepers[1]]
    return xi, captain, vice, bench


def _solve(
    players: pd.DataFrame,
    rules: Ruleset,
    score_col: str,
    current: CurrentSquad | None,
    max_transfers: int | None,
    lock: frozenset[int] = frozenset(),
    ban: frozenset[int] = frozenset(),
    force_start: frozenset[int] = frozenset(),
    force_bench: frozenset[int] = frozenset(),
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

    # Manager overlay constraints (CLAUDE.md rule 4): the human layer can pin
    # players in (lock: refuse to sell / must buy) or out (ban: refuse to own).
    for i in lock:
        if i in s:
            prob += s[i] == 1
    for i in ban:
        if i in s:
            prob += s[i] == 0
    # Manager start/bench overlay: force a player into or out of the XI (the
    # single-GW lineup fix below re-derives order, but these bind the MILP path
    # too — e.g. pre-season, no per-GW column). force_start implies owned.
    for i in force_start:
        if i in x:
            prob += x[i] == 1
    for i in force_bench:
        if i in x:
            prob += x[i] == 0

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


def _immediate_gw_col(columns) -> str | None:
    """The smallest-numbered per-GW column (`xpts_gw{n}`) = this week's fixture."""
    gw_cols = [(int(m.group(1)), c) for c in columns if (m := _GW_COL.match(str(c)))]
    return min(gw_cols)[1] if gw_cols else None


def optimize(
    projections: pd.DataFrame,
    rules: Ruleset | None = None,
    current: CurrentSquad | None = None,
    max_transfers: int | None = None,
    score_col: str = "xpts_horizon",
    allow_unverified: bool = False,
    lock: frozenset[int] = frozenset(),
    ban: frozenset[int] = frozenset(),
    force_start: frozenset[int] = frozenset(),
    force_bench: frozenset[int] = frozenset(),
    xi_score_col: str | None = None,
) -> OptimizedSquad:
    """Optimal squad from a projections table.

    current=None: initial build (GW1 / wildcard) within the rules budget.
    current given: transfer mode — buys/sells priced at sell_price(), hits
    charged beyond free transfers, and ev_delta populated with the objective
    gain over rolling the current squad unchanged (memos quote this against
    policies.hit_ev_threshold).

    Squad membership, transfers and hits are decided on `score_col` (the decayed
    multi-week horizon — you OWN a player for a run of fixtures). The starting
    XI, captain, vice and bench ORDER are single-GW decisions: when the table
    carries per-GW columns they default to `xi_score_col` (auto-detected as the
    nearest `xpts_gw{n}`), so a soft-fixture player is no longer benched behind a
    hard-fixture one on a bigger horizon total (backtest GW10). Pass
    xi_score_col=score_col to opt out. force_start/force_bench are the manager's
    XI overlay for reads the model can't see (backtest GW13 depleted defence).
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

    result = _solve(
        players, rules, score_col, current, max_transfers, lock, ban,
        force_start, force_bench,
    )
    if current is not None:
        baseline = _solve(
            players, rules, score_col, current, max_transfers=0,
            force_start=force_start, force_bench=force_bench,
        )
        result = OptimizedSquad(
            **{
                **result.__dict__,
                "ev_delta": round(result.objective - baseline.objective, 3),
            }
        )

    if xi_score_col is None:
        xi_score_col = _immediate_gw_col(players.columns)
    if xi_score_col and xi_score_col != score_col and xi_score_col in players.columns:
        by_id = players.set_index("id")
        pos = {i: by_id.loc[i, "position"] for i in result.squad}
        xi_score = {i: float(by_id.loc[i, xi_score_col]) for i in result.squad}
        xi, captain, vice, bench = _pick_lineup(
            result.squad, xi_score, pos, rules.raw["lineup"], force_start, force_bench
        )
        result = OptimizedSquad(
            **{
                **result.__dict__,
                "xi": sorted(xi, key=lambda i: (POSITIONS.index(pos[i]), -xi_score[i])),
                "captain": captain,
                "vice": vice,
                "bench": bench,
            }
        )
    return result

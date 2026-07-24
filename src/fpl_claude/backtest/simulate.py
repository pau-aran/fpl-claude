"""Season-replay simulator: run the real pipeline GW by GW against history.

Each gameweek the simulator does exactly what /fpl-plan-gameweek does live —
point-in-time projections (minutes x rates x team model), MILP squad/transfer
optimization, captain and bench order — then scores the picks against what
actually happened, with real FPL mechanics:

  - transfers priced at sell_price() with the tracked buy cost, bank respected
  - free-transfer banking (cap from rules), hits charged at rules hit_cost
  - hit discipline: a hit is only kept if the optimizer's ev_delta clears
    policies.hit_ev_threshold (CLAUDE.md rule 5)
  - captain doubles; vice takes over when the captain plays 0 minutes
  - autosubs in bench order, respecting the lineup formation minimums

The output per GW is a GWResult carrying both the decision (what we picked and
why the optimizer liked it) and the outcome (actual points), so the review loop
can separate process from variance (CLAUDE.md rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..models import projections as proj
from ..models.team import TeamModel
from ..optimize.milp import CurrentSquad, OptimizedSquad, optimize
from ..rules.engine import Ruleset
from .data import SeasonStore


@dataclass(frozen=True)
class ManagerDecision:
    """The human layer's call on top of the optimizer proposal (CLAUDE.md
    rule 4: models propose, we dispose). Every field is an explicit deviation
    with `reasoning` recorded in the memo — never a silent override.

    lock: players we refuse to sell (or insist on buying) this GW
    ban:  players we refuse to own this GW (e.g. rotation trap, news doubt)
    captain/vice: override the solver's pick (must be in the final XI)
    max_transfers: cap moves below the solver's allowance (e.g. force a roll)
    start/bench: force an owned player into / out of the XI when the human sees
        a fixture read the stats model can't (depleted opponent defence, a
        soft individual duel) — the bench-order override the reviews asked for
    """

    lock: frozenset[int] = frozenset()
    ban: frozenset[int] = frozenset()
    captain: int | None = None
    vice: int | None = None
    max_transfers: int | None = None
    start: frozenset[int] = frozenset()
    bench: frozenset[int] = frozenset()
    reasoning: str = ""


@dataclass
class SquadState:
    """What we own between deadlines. buy_costs/bank in API tenths."""

    buy_costs: dict[int, int]
    bank: int
    free_transfers: int
    points_total: int = 0
    hits_total: int = 0


@dataclass(frozen=True)
class GWResult:
    gw: int
    squad: OptimizedSquad
    predicted_xi_pts: float  # xPts for this GW: XI + captain double
    actual_pts: int  # after autosubs, captaincy and hit deduction
    hits: int
    bank: int
    free_transfers_left: int
    autosubs: list[tuple[int, int]]  # (out, in)
    effective_captain: int
    player_rows: pd.DataFrame  # per-squad-player predicted vs actual
    transfers: list[tuple[int, int]] = field(default_factory=list)  # (out, in) ids
    names: dict[int, str] = field(default_factory=dict)  # every projected player


def build_team_model(store: SeasonStore, gw: int) -> TeamModel | None:
    try:
        results = store.results_through(gw)
        if len(results) < 100:
            return None
        return TeamModel.fit(results)
    except ImportError:
        return None


def project_gw(
    store: SeasonStore,
    gw: int,
    rules: Ruleset,
    overlays: dict[int, dict[str, Any]] | None = None,
    horizon: int | None = None,
) -> pd.DataFrame:
    bootstrap = store.bootstrap_at(gw)
    fixtures = store.fixtures_at(gw)
    return proj.build_projections(
        bootstrap,
        fixtures,
        ruleset=rules,
        team_model=build_team_model(store, gw),
        prior_bootstrap=store.prior_bootstrap(),
        overlays=overlays,
        horizon=horizon,
    )


def initial_build(
    projections: pd.DataFrame, rules: Ruleset, decision: ManagerDecision | None = None
) -> tuple[OptimizedSquad, SquadState]:
    d = decision or ManagerDecision()
    squad = optimize(
        projections, rules=rules, lock=d.lock, ban=d.ban,
        force_start=d.start, force_bench=d.bench,
    )
    prices = projections.drop_duplicates("id").set_index("id")["price"]
    buy_costs = {i: int(round(prices.loc[i] * 10)) for i in squad.squad}
    budget = int(rules.raw["budget"]["initial"] * 10)
    return squad, SquadState(
        buy_costs=buy_costs, bank=budget - squad.cost, free_transfers=1
    )


def decide_transfers(
    projections: pd.DataFrame,
    rules: Ruleset,
    state: SquadState,
    max_extra_transfers: int = 1,
    decision: ManagerDecision | None = None,
) -> tuple[OptimizedSquad, dict]:
    """Optimizer proposes; the hit policy and manager overlay dispose.

    Hits are gated on their MARGINAL NET value: the hit-taking solution must
    beat the best hit-free solution by hit_ev_threshold PER HIT, with the -4
    already charged — a hit that merely breaks even on paper is noise-chasing
    (early-season projections are not horizon-stable truth). Gating the whole
    package let a +2.5 hit ride in on a +13 free move (GW2 review); gating at
    net +0.5 would still have passed it (GW3 review).

    Returns (squad, audit) — audit records the gate outcome for the memo.
    """
    d = decision or ManagerDecision()
    current = CurrentSquad(
        buy_costs=dict(state.buy_costs),
        bank=state.bank,
        free_transfers=state.free_transfers,
    )
    allowance = state.free_transfers + max_extra_transfers
    if d.max_transfers is not None:
        allowance = min(allowance, d.max_transfers)
    result = optimize(
        projections, rules=rules, current=current, max_transfers=allowance,
        lock=d.lock, ban=d.ban, force_start=d.start, force_bench=d.bench,
    )
    audit: dict = {"hit_gate": "n/a", "hit_marginal": None}
    if result.hits > 0:
        free = optimize(
            projections, rules=rules, current=current,
            max_transfers=min(state.free_transfers, allowance),
            lock=d.lock, ban=d.ban, force_start=d.start, force_bench=d.bench,
        )
        threshold = float(rules.policy("hit_ev_threshold"))
        marginal = result.objective - free.objective  # already net of hit cost
        audit["hit_marginal"] = round(marginal, 2)
        if marginal < threshold * result.hits:
            audit["hit_gate"] = f"rejected: net {audit['hit_marginal']} < {threshold}/hit"
            result = free
        else:
            audit["hit_gate"] = f"kept: net {audit['hit_marginal']} >= {threshold}/hit"
    return result, audit


def apply_captaincy(squad: OptimizedSquad, decision: ManagerDecision) -> OptimizedSquad:
    """Manager captain/vice override — only within the solver's XI."""
    captain = decision.captain if decision.captain in squad.xi else squad.captain
    vice = decision.vice if decision.vice in squad.xi else squad.vice
    if vice == captain:  # keep them distinct, demote to solver's alternative
        vice = squad.captain if squad.captain != captain else squad.vice
    if captain == squad.captain and vice == squad.vice:
        return squad
    return OptimizedSquad(**{**squad.__dict__, "captain": captain, "vice": vice})


def apply_transfers(
    state: SquadState, squad: OptimizedSquad, projections: pd.DataFrame, rules: Ruleset
) -> SquadState:
    prices = projections.drop_duplicates("id").set_index("id")["price"]
    buy_costs = dict(state.buy_costs)
    bank = state.bank
    for pid in squad.transfers_out:
        bank += rules.sell_price(buy_costs.pop(pid), int(round(prices.loc[pid] * 10)))
    for pid in squad.transfers_in:
        cost = int(round(prices.loc[pid] * 10))
        buy_costs[pid] = cost
        bank -= cost
    n = len(squad.transfers_in)
    cap = int(rules.raw["transfers"]["max_banked"])
    free_left = max(0, state.free_transfers - n)
    return SquadState(
        buy_costs=buy_costs,
        bank=bank,
        free_transfers=min(cap, free_left + 1),  # next GW's budget
        points_total=state.points_total,
        hits_total=state.hits_total,
    )


def _autosub(
    xi: list[int],
    bench: list[int],
    minutes: dict[int, int],
    positions: dict[int, str],
    rules: Ruleset,
) -> tuple[list[int], list[tuple[int, int]]]:
    """FPL autosub: replace 0-minute starters from the bench in order, keeping
    the lineup legal (exact GK count, positional minimums from rules)."""
    lineup = rules.raw["lineup"]
    minimum = {
        "GKP": int(lineup["min_goalkeepers"]),
        "DEF": int(lineup["min_defenders"]),
        "MID": int(lineup["min_midfielders"]),
        "FWD": int(lineup["min_forwards"]),
    }
    final = list(xi)
    available = [b for b in bench if minutes.get(b, 0) > 0]
    subs: list[tuple[int, int]] = []
    for starter in xi:
        if minutes.get(starter, 0) > 0:
            continue
        pos_out = positions[starter]
        count = lambda pos: sum(1 for i in final if positions[i] == pos)  # noqa: E731
        for candidate in list(available):
            pos_in = positions[candidate]
            if pos_out == "GKP" and pos_in != "GKP":
                continue  # keeper can only be replaced by a keeper
            if pos_in == "GKP" and pos_out != "GKP":
                continue
            if pos_in != pos_out and count(pos_out) - 1 < minimum[pos_out]:
                continue  # dropping below the formation minimum
            final.remove(starter)
            final.append(candidate)
            available.remove(candidate)
            subs.append((starter, candidate))
            break
    return final, subs


def score_gw(
    store: SeasonStore,
    gw: int,
    squad: OptimizedSquad,
    projections: pd.DataFrame,
    rules: Ruleset,
) -> tuple[int, list[tuple[int, int]], int, pd.DataFrame]:
    """Actual points for the picked squad in GW `gw` (before hit deduction).

    Returns (points, autosubs, effective_captain, per-player table).
    """
    actual = store.actuals(gw).set_index("id")
    pts = actual["points"].to_dict()
    mins = actual["minutes"].to_dict()
    by_id = projections.drop_duplicates("id").set_index("id")
    positions = {i: by_id.loc[i, "position"] for i in squad.squad}

    final_xi, subs = _autosub(squad.xi, squad.bench, mins, positions, rules)

    captain = squad.captain
    if mins.get(captain, 0) == 0 and mins.get(squad.vice, 0) > 0:
        captain = squad.vice

    total = sum(int(pts.get(i, 0)) for i in final_xi)
    if captain in final_xi:
        total += int(pts.get(captain, 0))  # double counts once more

    xpts_col = f"xpts_gw{gw}"
    rows = []
    for i in squad.squad:
        rows.append(
            {
                "id": i,
                "web_name": by_id.loc[i, "web_name"],
                "team": by_id.loc[i, "team"],
                "position": positions[i],
                "price": by_id.loc[i, "price"],
                "predicted": float(by_id.loc[i].get(xpts_col, 0.0)),
                "actual": int(pts.get(i, 0)),
                "minutes": int(mins.get(i, 0)),
                "role": (
                    "C" if i == squad.captain
                    else "V" if i == squad.vice
                    else "XI" if i in squad.xi
                    else "bench"
                ),
                "played_after_subs": i in final_xi,
            }
        )
    return total, subs, captain, pd.DataFrame(rows)


def predicted_xi_points(squad: OptimizedSquad, projections: pd.DataFrame, gw: int) -> float:
    col = f"xpts_gw{gw}"
    by_id = projections.drop_duplicates("id").set_index("id")
    if col not in by_id.columns:
        return 0.0
    total = sum(float(by_id.loc[i, col]) for i in squad.xi)
    return round(total + float(by_id.loc[squad.captain, col]), 2)


def run_gameweek(
    store: SeasonStore,
    gw: int,
    rules: Ruleset,
    state: SquadState | None,
    overlays: dict[int, dict[str, Any]] | None = None,
    decision: ManagerDecision | None = None,
) -> tuple[GWResult, SquadState]:
    """One full deadline cycle: project -> propose -> manager call -> score."""
    projections = project_gw(store, gw, rules, overlays=overlays)

    if state is None:
        squad, state = initial_build(projections, rules, decision=decision)
    else:
        squad, _ = decide_transfers(projections, rules, state, decision=decision)
        state = apply_transfers(state, squad, projections, rules)
    if decision is not None:
        squad = apply_captaincy(squad, decision)

    raw_pts, subs, eff_captain, player_rows = score_gw(store, gw, squad, projections, rules)
    hit_cost = int(rules.raw["transfers"]["hit_cost"])
    net = raw_pts - squad.hits * hit_cost

    state.points_total += net
    state.hits_total += squad.hits

    result = GWResult(
        gw=gw,
        squad=squad,
        predicted_xi_pts=predicted_xi_points(squad, projections, gw),
        actual_pts=net,
        hits=squad.hits,
        bank=state.bank,
        free_transfers_left=state.free_transfers,
        autosubs=subs,
        effective_captain=eff_captain,
        player_rows=player_rows,
        transfers=list(zip(squad.transfers_out, squad.transfers_in)),
        names=dict(
            zip(projections.drop_duplicates("id")["id"], projections.drop_duplicates("id")["web_name"])
        ),
    )
    return result, state

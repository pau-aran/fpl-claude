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
from ..optimize.chip_timing import HALF_BOUNDARY_GW
from ..optimize.milp import CurrentSquad, OptimizedSquad, optimize
from ..optimize.transfer_path import plan_transfer_path
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
    chip: str | None = None  # one of CHIPS (wildcard/free_hit/bench_boost/triple_captain)
    reasoning: str = ""


# Canonical chip names (2025/26: two sets per half-season). Aliases map to these.
CHIPS = frozenset({"wildcard", "free_hit", "bench_boost", "triple_captain"})
_CHIP_ALIASES = {
    "wc": "wildcard", "fh": "free_hit", "bb": "bench_boost", "tc": "triple_captain",
    "3xc": "triple_captain", "triplecaptain": "triple_captain", "benchboost": "bench_boost",
    "freehit": "free_hit",
}


def canonical_chip(chip: str | None) -> str | None:
    """Normalise a chip name; raise on an unknown one (a typo must not silently no-op)."""
    if chip is None:
        return None
    key = str(chip).strip().lower().replace(" ", "_").replace("-", "_")
    key = _CHIP_ALIASES.get(key, key)
    if key not in CHIPS:
        raise ValueError(f"unknown chip {chip!r}; expected one of {sorted(CHIPS)} (or an alias)")
    return key


@dataclass
class SquadState:
    """What we own between deadlines. buy_costs/bank in API tenths."""

    buy_costs: dict[int, int]
    bank: int
    free_transfers: int
    points_total: int = 0
    hits_total: int = 0
    chips_used: list[str] = field(default_factory=list)  # e.g. ["triple_captain@17"]


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
    chip: str | None = None  # chip played this GW, if any
    # predicted_xi_pts split (A2 calibration): the season-long prediction residual
    # lives ~entirely in these two slots being read together — the base XI runs a
    # small within-noise mean under-prediction while the doubled captain is a
    # mean-unbiased ±10 coin. Logging them apart lets EV/hit-gate reporting be read
    # against the known captain-slot variance (see reports/backtest/2025-26/calibration.md).
    base_xi_pts: float = 0.0  # counted players' xPts, captain EXCLUDED
    captain_slot_pts: float = 0.0  # captain xPts x captain_mult (the doubled/tripled slot)
    captain_mult: int = 2  # 2 normal / bench_boost, 3 triple_captain


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
    follow_path: bool = False,
) -> tuple[OptimizedSquad, dict]:
    """Optimizer proposes; the hit policy and manager overlay dispose.

    Hits are gated on their MARGINAL NET value: the hit-taking solution must
    beat the best hit-free solution by hit_ev_threshold PER HIT, with the -4
    already charged — a hit that merely breaks even on paper is noise-chasing
    (early-season projections are not horizon-stable truth). Gating the whole
    package let a +2.5 hit ride in on a +13 free move (GW2 review); gating at
    net +0.5 would still have passed it (GW3 review).

    `follow_path` (OPT-IN, default OFF — A4) hands the transfer choice to the
    multi-period planner (`optimize.transfer_path`) instead: its THIS-WEEK step
    is pinned into the single-period solve (buys locked, sells banned, allowance
    set to the step's size) so the squad/XI/captain still come from the normal
    optimizer, but WHICH moves are made — including rolling toward a later
    window — is the path's call. It is off by default deliberately: every
    committed backtest result was produced by the single-period route, and the
    planner's forward steps rest on projections that are provisional past the
    immediate GW. A manager transfer CAP tighter than the path's step wins, in
    which case this falls back to the standard route.

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

    if follow_path:
        path = plan_transfer_path(projections, rules, current, lock=d.lock, ban=d.ban)
        step = path.this_week
        if d.max_transfers is None or d.max_transfers >= step.n_moves:
            result = optimize(
                projections, rules=rules, current=current, max_transfers=step.n_moves,
                lock=d.lock | frozenset(step.in_ids),
                ban=d.ban | frozenset(step.out_ids),
                force_start=d.start, force_bench=d.bench,
            )
            return result, {
                "hit_gate": path.hit_gate,
                "hit_marginal": None,
                "path_verdict": path.verdict,
                "path_roll_gain": path.roll_gain,
                "path_edge_floor": path.edge_floor,
                "path_rationale": path.rationale,
            }
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
    chip: str | None = None,
) -> tuple[int, list[tuple[int, int]], int, pd.DataFrame]:
    """Actual points for the picked squad in GW `gw` (before hit deduction).

    Chips (Phase 3b): `bench_boost` scores all 15 (no autosubs — every player
    counts); `triple_captain` triples the captain instead of doubling. `wildcard`
    / `free_hit` are transfer-side chips handled in run_gameweek; here they score
    like a normal week (the FH/WC squad is passed in as `squad`).

    Returns (points, autosubs, effective_captain, per-player table).
    """
    chip = canonical_chip(chip)
    actual = store.actuals(gw).set_index("id")
    pts = actual["points"].to_dict()
    mins = actual["minutes"].to_dict()
    by_id = projections.drop_duplicates("id").set_index("id")
    positions = {i: by_id.loc[i, "position"] for i in squad.squad}

    if chip == "bench_boost":
        final_xi, subs = list(squad.squad), []  # all 15 count; autosubs moot
    else:
        final_xi, subs = _autosub(squad.xi, squad.bench, mins, positions, rules)

    captain = squad.captain
    if mins.get(captain, 0) == 0 and mins.get(squad.vice, 0) > 0:
        captain = squad.vice

    total = sum(int(pts.get(i, 0)) for i in final_xi)
    if captain in final_xi:
        # normal: +1 (double); triple captain: +2 (triple)
        total += (2 if chip == "triple_captain" else 1) * int(pts.get(captain, 0))

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


@dataclass(frozen=True)
class XiBreakdown:
    """The predicted-XI total split into the two slots the A2 calibration work
    isolated: a base XI (every counted player EXCEPT the captain) plus the
    captain slot (the captain's xPts multiplied by how many times he counts —
    2 normally / on bench_boost, 3 on triple_captain). `total` is exactly what
    `predicted_xi_points` returns; base_xi + captain_slot == total by construction.
    """

    total: float
    base_xi: float
    captain_slot: float
    captain_mult: int


def predicted_xi_breakdown(
    squad: OptimizedSquad, projections: pd.DataFrame, gw: int, chip: str | None = None
) -> XiBreakdown:
    """Predicted XI points, split into base XI vs the doubled/tripled captain slot.

    The season backtest showed the reported prediction error is not a single
    level bias: the base XI carries a small (within-noise) mean under-prediction
    while the captain slot is mean-unbiased but high-variance (±~10 doubled). The
    memo Outcome shows the split so EV is read against that known structure, not
    as one opaque total. Applies forward-only; committed memos are untouched.
    """
    chip = canonical_chip(chip)
    col = f"xpts_gw{gw}"
    by_id = projections.drop_duplicates("id").set_index("id")
    cap_mult = 3 if chip == "triple_captain" else 2
    if col not in by_id.columns:
        return XiBreakdown(0.0, 0.0, 0.0, cap_mult)
    counted = squad.squad if chip == "bench_boost" else squad.xi
    cap_xpts = float(by_id.loc[squad.captain, col])
    base_xi = sum(float(by_id.loc[i, col]) for i in counted if i != squad.captain)
    captain_slot = cap_mult * cap_xpts
    return XiBreakdown(
        total=round(base_xi + captain_slot, 2),
        base_xi=round(base_xi, 2),
        captain_slot=round(captain_slot, 2),
        captain_mult=cap_mult,
    )


def predicted_xi_points(
    squad: OptimizedSquad, projections: pd.DataFrame, gw: int, chip: str | None = None
) -> float:
    return predicted_xi_breakdown(squad, projections, gw, chip=chip).total


def wildcard_squad(
    projections: pd.DataFrame,
    rules: Ruleset,
    state: SquadState,
    decision: ManagerDecision | None = None,
) -> OptimizedSquad:
    """Best squad reachable this GW with UNLIMITED FREE transfers (wildcard /
    free hit): same budget maths as a normal transfer solve (spend on buys must
    fit bank + sale proceeds), but every transfer is free — model it by handing
    the solver a free-transfer allowance equal to the squad size, so `hits` is
    driven to zero and `max_transfers` is unbound. Manager lock/ban/start/bench
    overlays still apply (e.g. ban an AFCON player so the WC can't buy him)."""
    d = decision or ManagerDecision()
    size = int(rules.raw["squad"]["size"])
    current = CurrentSquad(
        buy_costs=dict(state.buy_costs), bank=state.bank, free_transfers=size
    )
    return optimize(
        projections, rules=rules, current=current, max_transfers=None,
        lock=d.lock, ban=d.ban, force_start=d.start, force_bench=d.bench,
    )


# HALF_BOUNDARY_GW lives in optimize.chip_timing (the timing layer owns the chip
# calendar) and is imported at the top; re-exported here for existing call sites.


def _chip_half(gw: int) -> int:
    return 1 if gw <= HALF_BOUNDARY_GW else 2


def _assert_chip_available(chip: str, gw: int, state: SquadState) -> None:
    """One of each chip per half-season (2025/26). Raise if already spent this half."""
    half = _chip_half(gw)
    for used in state.chips_used:
        name, _, used_gw = used.partition("@")
        if name == chip and used_gw.isdigit() and _chip_half(int(used_gw)) == half:
            raise ValueError(
                f"chip {chip!r} already used in half {half} (at GW{used_gw}); "
                "one of each chip per half-season"
            )


def run_gameweek(
    store: SeasonStore,
    gw: int,
    rules: Ruleset,
    state: SquadState | None,
    overlays: dict[int, dict[str, Any]] | None = None,
    decision: ManagerDecision | None = None,
    follow_path: bool = False,
) -> tuple[GWResult, SquadState]:
    """One full deadline cycle: project -> propose -> manager call -> score.

    `follow_path` hands transfer choice to the multi-period planner (see
    `decide_transfers`) — EXPERIMENTAL, off for every committed result.

    Chips (Phase 3b), all via decision.chip:
      wildcard      unlimited FREE transfers, squad kept; next-GW FT resets to 1.
      free_hit      unlimited free transfers for THIS GW only; squad + bank revert
                    next GW; FTs are untouched (roll as if no transfer was made).
      bench_boost   all 15 score this GW (no autosubs); transfers as normal.
      triple_captain captain scores 3x this GW; transfers as normal.
    """
    projections = project_gw(store, gw, rules, overlays=overlays)
    chip = canonical_chip(decision.chip if decision else None)
    if chip and state is not None:
        _assert_chip_available(chip, gw, state)
    hit_cost = int(rules.raw["transfers"]["hit_cost"])
    cap = int(rules.raw["transfers"]["max_banked"])

    pre_state = state  # for free_hit revert
    if state is None:
        squad, state = initial_build(projections, rules, decision=decision)
    elif chip in ("wildcard", "free_hit"):
        # Rebuild with unlimited free transfers (milp.optimize with FT = squad size).
        squad = wildcard_squad(projections, rules, state, decision=decision)
        if chip == "wildcard":
            state = apply_transfers(state, squad, projections, rules)  # n>FT ⇒ next FT = 1
        else:  # free_hit: score the temp squad, revert squad+bank, roll FTs
            state = SquadState(
                buy_costs=dict(pre_state.buy_costs),
                bank=pre_state.bank,
                free_transfers=min(cap, pre_state.free_transfers + 1),
                points_total=pre_state.points_total,
                hits_total=pre_state.hits_total,
                chips_used=list(pre_state.chips_used),
            )
    else:
        squad, _ = decide_transfers(
            projections, rules, state, decision=decision, follow_path=follow_path
        )
        state = apply_transfers(state, squad, projections, rules)
    # optimize() already fields the XI/captain/bench on THIS week's fixture column
    # (milp._pick_lineup) and honours any force_start/force_bench overlay.
    if decision is not None:
        squad = apply_captaincy(squad, decision)

    raw_pts, subs, eff_captain, player_rows = score_gw(
        store, gw, squad, projections, rules, chip=chip
    )
    net = raw_pts - squad.hits * hit_cost

    state.points_total += net
    state.hits_total += squad.hits
    if chip:
        state.chips_used = [*state.chips_used, f"{chip}@{gw}"]

    breakdown = predicted_xi_breakdown(squad, projections, gw, chip=chip)
    result = GWResult(
        gw=gw,
        squad=squad,
        predicted_xi_pts=breakdown.total,
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
        chip=chip,
        base_xi_pts=breakdown.base_xi,
        captain_slot_pts=breakdown.captain_slot,
        captain_mult=breakdown.captain_mult,
    )
    return result, state

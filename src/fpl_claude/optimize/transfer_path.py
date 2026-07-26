"""Multi-period transfer PATH planner — which moves, in WHICH gameweek.

`milp.optimize` answers "what is the best squad for the decayed horizon, this
week". It cannot answer the question the AFCON window actually turned on:
*should we spend the free transfer now, or bank it for the gameweek where the
returnee/fixture swing pays?* That logic has lived as a hand-written
`reports/backtest/2025-26/plan.md` overlay (worth ~+56 pts over GW17-24). This
module makes it MODEL-DERIVED: one MILP over the whole horizon, squad membership
and transfers indexed by (player, gameweek), free transfers accumulating with the
banking cap, hits charged per gameweek, budget carried across periods.

The output is a CANDIDATE PATH, never an order (CLAUDE.md rule 4). Nothing here
writes state, plays a chip or executes a transfer; the caller prints it and the
manager overlays what the model cannot see. It answers exactly the three
questions a decision memo needs:

  1. what to do THIS week                  -> TransferPath.this_week
  2. what the plan expects to do next      -> TransferPath.forward
  3. what BANKING the free transfer is worth -> TransferPath.roll_gain
     (= objective of the best path that rolls this week MINUS the objective of
     the best path that moves this week; positive means banking wins by that
     many decayed points over the horizon)

Every constraint value comes from the rules engine — squad shape, club cap,
lineup minimums, `transfers.free_per_gameweek`, `transfers.max_banked`,
`transfers.hit_cost`, `budget.sell_price_rule` via `Ruleset.sell_price`,
`policies.hit_ev_threshold`, `policies.horizon_decay`. No rule number is
hard-coded here; every number that IS hard-coded is a modelling choice, and each
one is a named constant below so a review can argue with the number rather than
reverse-engineer it.

WHY A TRUE MULTI-PERIOD MILP (and not a greedy "should I roll?" heuristic)
-------------------------------------------------------------------------
A greedy planner can only compare "best move now" with "best move now, deferred
one week". The GW17-24 window needed the other shape: bank across THREE weeks so
that GW22 and GW24 could each be taken free, with the budget from a GW22 sale
funding the GW24 buy. Only a model with transfer variables in every period and
FT/bank state linking them can price that; so the planner solves the real thing
and pays for it with an aggressively pruned player pool (below).

SIMPLIFICATIONS — named honestly, and surfaced in TransferPath.caveats
----------------------------------------------------------------------
* **Prices are static.** The projections table carries one `price` per player and
  no per-GW price path, so a player bought inside the horizon sells for exactly
  what he cost (which is what `sell_price` returns for a zero-profit hold — so
  this is exact under the "no price change" assumption, not an approximation of
  the sell rule itself). Owned players use the true tracked
  `rules.sell_price(buy_cost, current_price)`. Real price rises/falls inside a
  4-5 week window are worth ~£0.1-0.3m and are NOT modelled.
* **No buy-back inside the horizon** (`buy` is forced to zero for owned players,
  and every player may be bought at most once). This keeps each player's sale
  price a single constant — the thing that would otherwise need a per-purchase
  cost variable — and it happens to encode a proven rule: never re-buy what you
  just sold without new information (knowledge.md, GW3 Wood veto).
* **No chips.** Wildcards/free hits would make transfers free in one period; chip
  TIMING is `chip_timing.advise`'s job and the two are read side by side. A path
  that wants 4+ changes in one week is a WILDCARD conversation, which is why
  `MAX_MOVES_PER_GW` sits just below `chip_timing.WC_CHANGE_THRESHOLD`.
* **Bench value is the flat `milp.BENCH_WEIGHT` fraction** and no vice variable is
  carried (a 15x T binary block for a `VICE_WEIGHT`-sized effect). Autosubs and
  bench ORDER are single-GW decisions `milp.optimize`/`_pick_lineup` make at the
  deadline; this planner only decides WHO to own WHEN.
* **Minutes/availability are the projection's, frozen.** The per-GW columns
  already carry the news overlay at solve time; the planner cannot know about a
  knock that happens in GW+2. Every forward step is therefore provisional and the
  path is re-solved at each deadline.
* **Future projections are discounted** by `policies.horizon_decay` per step
  (the same weighting `models/projections.py` uses to build `xpts_horizon`), so
  the planner's objective is comparable with the single-period optimizer's. HIT
  COSTS ARE NOT DISCOUNTED: a -4 is a certain cost while a future gain is a
  discounted guess, and being conservative about scheduling future hits is the
  behaviour we want.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pulp

from ..rules.engine import Ruleset
from .chip_timing import _gw_columns
from .milp import (
    BENCH_WEIGHT,
    POSITIONS,
    CurrentSquad,
    InfeasibleError,
    RulesetUnverifiedError,
)

# ---------------------------------------------------------------- constants
# All tractability/behaviour knobs are explicit so a review can argue with the
# number. The player pool is the whole ballgame: a 600-player x 5-GW model is
# ~12,000 binaries before the lineup block and will not solve inside a deadline.

# Top-N per position by horizon points. 16 is chosen so the four positional
# blocks (16 x 4 = 64) plus the owned 15 stay near ~75 players; at 5 periods that
# is ~1,900 binaries, which HiGHS closes in seconds. The trade-off is real: a
# genuine target ranked 17th at his position is invisible to the PATH, though he
# is still visible to the single-period `milp.optimize` the memo runs alongside.
POOL_TOP_N_PER_POSITION = 16

# ...plus the top-N per position by points-per-£m. Ranking purely by total points
# fills the pool with premiums the bank cannot fund, and the multi-period model
# lives or dies on FUNDING ROUTES (sell A in GW+1 to afford B in GW+2). These are
# the cheap enablers that make a route foot.
POOL_TOP_N_VALUE_PER_POSITION = 8

# How many future gameweeks the path plans over. `policies.planning_horizon_gws`
# (8) is the projection horizon; planning all 8 is neither tractable nor honest —
# week-7 minutes are a guess and the path is re-solved every deadline anyway.
# 5 matches the fixture-outlook window the memos already print.
MAX_PLANNING_GWS = 5

# Moves allowed in a single gameweek. Above this the question is not "which
# transfers" but "should we wildcard" — kept one below
# chip_timing.WC_CHANGE_THRESHOLD (4) so the two advisories can never both claim
# the same reshape.
MAX_MOVES_PER_GW = 3

# Below this many decayed points, the roll-vs-move call is a coin flip and the
# memo should say so rather than dress a rounding difference as a plan. ~0.5 is
# the noise floor the hit-gate work settled on for "not a real edge".
ROLL_DECISIVE_EDGE = 0.5

# Wall-clock cap per solve. Three solves (path, roll-forced, move-forced) run per
# advisory, so the worst case is ~3x this. A time-limited incumbent is accepted
# and flagged in the caveats — a good path found in 60s beats a proven-optimal
# one found after the deadline.
SOLVER_TIME_LIMIT_SECONDS = 60

# A hair of objective per banked free transfer. This is NOT a claim about what an
# FT is worth (the planner prices that properly, via roll_gain) — it exists so the
# REPORTED free-transfer trajectory is pinned to the true banking maximum instead
# of an arbitrary point in a degenerate optimum, and so exact ties break toward
# optionality. Three orders of magnitude below a single point, it cannot move a
# real decision.
FT_TIEBREAK_BONUS = 1e-3


# ------------------------------------------------------------------- results


@dataclass(frozen=True)
class PlannedMove:
    """One gameweek's step in the path. `out_ids`/`in_ids` are paired by position
    in the list only for display — the MILP chooses a SET of moves, not ordered
    pairs. `gw_xpts` is the XI + captain total on that gameweek's OWN column
    (undecayed, so it reads like a real score), while the path objective that
    ranked this plan uses the decayed weighting."""

    gw: int
    out_ids: tuple[int, ...]
    in_ids: tuple[int, ...]
    out_names: tuple[str, ...]
    in_names: tuple[str, ...]
    hits: int
    free_transfers_before: int  # FTs available going INTO this gameweek
    free_transfers_after: int  # ...left once this gameweek's moves are paid for
    free_transfers_next: int  # ...carried into the NEXT gameweek (after +1, capped)
    bank_after: int  # API tenths of £m
    gw_xpts: float

    @property
    def is_roll(self) -> bool:
        return not self.in_ids

    @property
    def n_moves(self) -> int:
        return len(self.in_ids)

    @property
    def summary(self) -> str:
        """The move without its gameweek label — 'Semenyo -> Bruno G. (1 FT, free)'."""
        if self.is_roll:
            return (
                f"ROLL, banking {self.free_transfers_before}"
                f" -> {self.free_transfers_next} FT"
            )
        moves = ", ".join(f"{o} -> {i}" for o, i in zip(self.out_names, self.in_names))
        cost = f"{self.hits} hit(s)" if self.hits else "free"
        return f"{moves} ({self.free_transfers_before} FT, {cost})"

    def describe(self) -> str:
        """One-line human form, e.g. 'GW22: Semenyo -> Bruno G. (1 FT, free)'."""
        return f"GW{self.gw}: {self.summary}"


@dataclass(frozen=True)
class TransferPath:
    """The planner's answer. `this_week` is the recommendation for the immediate
    deadline; `forward` is what the plan EXPECTS to do afterwards (provisional —
    re-solved every week); `roll_gain` prices banking the free transfer.

    objective/roll_objective/move_objective are decayed-horizon points including
    the bench fraction and net of hit costs, so they are only comparable with each
    other — quote `roll_gain`, never a bare objective, in a memo.
    """

    gws: tuple[int, ...]
    this_week: PlannedMove
    forward: tuple[PlannedMove, ...]  # every later period, rolls included (the FT trajectory)
    objective: float
    roll_objective: float | None
    move_objective: float | None
    roll_gain: float | None  # roll_objective - move_objective; >0 => bank the FT
    verdict: str  # "roll" | "move"
    hit_gate: str
    pool_size: int
    truncated: bool  # a solve hit SOLVER_TIME_LIMIT_SECONDS (incumbent, not proven optimal)
    rationale: str
    caveats: tuple[str, ...]

    @property
    def horizon_gws(self) -> int:
        return len(self.gws)

    @property
    def forward_moves(self) -> tuple[PlannedMove, ...]:
        """The later periods that actually TRANSFER — the plan's queued steps."""
        return tuple(m for m in self.forward if not m.is_roll)

    @property
    def decisive(self) -> bool:
        """Is the roll-vs-move edge big enough to be worth writing down as a call?"""
        return self.roll_gain is not None and abs(self.roll_gain) >= ROLL_DECISIVE_EDGE


# ----------------------------------------------------------------- the model


def _solver() -> pulp.LpSolver:
    """HiGHS with a wall-clock cap, CBC fallback — mirrors milp._solver but
    time-limited, because a multi-period model can otherwise chase the last 0.01
    of an objective past a deadline."""
    try:
        solver = pulp.HiGHS(msg=False, timeLimit=SOLVER_TIME_LIMIT_SECONDS)
        if solver.available():
            return solver
    except Exception:  # noqa: BLE001, S110 — any HiGHS wiring issue means fall back
        pass
    return pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT_SECONDS)


def horizon_columns(
    projections: pd.DataFrame, horizon: int | None = None
) -> list[tuple[int, str]]:
    """The per-GW score columns to plan over: `[(gw, 'xpts_gw{gw}'), ...]` in
    gameweek order, truncated to `horizon` (default MAX_PLANNING_GWS).

    Degradation is deliberate and total: one `xpts_gw` column gives a single
    period (the planner collapses to a one-week answer with an empty forward
    path), and a table with NO per-GW columns falls back to `xpts_horizon` as one
    pseudo-period labelled gw 0. Neither case raises.
    """
    limit = MAX_PLANNING_GWS if horizon is None else max(1, int(horizon))
    cols = _gw_columns(projections.columns)[:limit]
    if cols:
        return cols
    if "xpts_horizon" in projections.columns:
        return [(0, "xpts_horizon")]
    raise ValueError(
        "projections table has no xpts_gw{n} columns and no xpts_horizon fallback"
    )


def prune_pool(
    projections: pd.DataFrame,
    owned: set[int],
    keep: frozenset[int] = frozenset(),
    top_n: int = POOL_TOP_N_PER_POSITION,
    top_n_value: int = POOL_TOP_N_VALUE_PER_POSITION,
) -> pd.DataFrame:
    """Shrink the pool to something a 5-period MILP can solve.

    Kept: every OWNED player (they must be sellable, and rolling the current
    squad has to stay feasible — that is what guarantees the model never goes
    infeasible), every `keep` id (the manager's locks), the top `top_n` per
    position by `xpts_horizon`, and the top `top_n_value` per position by
    `xpts_per_m` (the cheap enablers that make funding routes foot). Ranking
    columns fall back to the summed per-GW columns / points-per-price if the
    projections table lacks them.
    """
    players = projections.drop_duplicates(subset="id").copy()
    gw_cols = [c for _gw, c in _gw_columns(players.columns)]
    if "xpts_horizon" not in players.columns:
        players["xpts_horizon"] = (
            players[gw_cols].sum(axis=1) if gw_cols else 0.0
        )
    if "xpts_per_m" not in players.columns:
        price = players["price"].astype(float)
        players["xpts_per_m"] = (
            players["xpts_horizon"] / price.where(price > 0, other=1.0)
        ).fillna(0.0)

    ids: set[int] = {int(i) for i in owned} | {int(i) for i in keep}
    for position in POSITIONS:
        block = players[players["position"] == position]
        ids |= {int(i) for i in block.nlargest(top_n, "xpts_horizon")["id"]}
        ids |= {int(i) for i in block.nlargest(top_n_value, "xpts_per_m")["id"]}
    return players[players["id"].isin(ids)].reset_index(drop=True)


@dataclass(frozen=True)
class _PathSolution:
    """Raw solve output before the roll/move comparison dresses it as advice."""

    moves: tuple[PlannedMove, ...]
    objective: float
    truncated: bool


def _solve_path(
    pool: pd.DataFrame,
    rules: Ruleset,
    current: CurrentSquad,
    periods: list[tuple[int, str]],
    lock: frozenset[int],
    ban: frozenset[int],
    first_move: str | None = None,  # None | "roll" | "move"
    allow_first_hit: bool = True,
) -> _PathSolution:
    """The multi-period MILP itself.

    Variables per (player, period): `own` (in the squad for that GW), `xi`,
    `cap`, `buy`, `sell`. Per period: `ft` (free transfers going INTO the
    gameweek, integer, capped at `transfers.max_banked`) and `hit` (paid
    transfers). Squad continuity chains the periods
    (`own[t] = own[t-1] + buy[t] - sell[t]`, seeded from the current squad); the
    FT recursion is the banking rule (`ft[t] <= ft[t-1] - moves + hits + free per
    GW`, capped); the bank constraint is cumulative so sale proceeds in GW t fund
    a buy in GW t+2.
    """
    shape = rules.squad_shape()
    lineup = rules.raw["lineup"]
    max_per_club = int(rules.raw["squad"]["max_per_club"])
    hit_cost = float(rules.raw["transfers"]["hit_cost"])
    ft_cap = int(rules.raw["transfers"]["max_banked"])
    ft_per_gw = int(rules.raw["transfers"]["free_per_gameweek"])
    decay = float(rules.policy("horizon_decay"))

    ids = [int(i) for i in pool["id"]]
    by_id = pool.set_index("id")
    price = {i: round(float(by_id.loc[i, "price"]) * 10) for i in ids}
    pos = {i: str(by_id.loc[i, "position"]) for i in ids}
    club = {i: by_id.loc[i, "team"] for i in ids}
    name = {
        i: str(by_id.loc[i, "web_name"]) if "web_name" in by_id.columns else str(i)
        for i in ids
    }
    owned = {i for i in ids if i in current.buy_costs}
    # Sale value: tracked buy cost for what we hold; purchase price for anything
    # bought inside the horizon (prices are static — see the module docstring).
    sale = {
        i: (
            rules.sell_price(int(current.buy_costs[i]), price[i])
            if i in owned
            else price[i]
        )
        for i in ids
    }
    T = len(periods)
    score = {
        (i, t): float(by_id.loc[i, col]) for i in ids for t, (_gw, col) in enumerate(periods)
    }
    weight = [decay**t for t in range(T)]

    prob = pulp.LpProblem("fpl_transfer_path", pulp.LpMaximize)
    keys = [(i, t) for i in ids for t in range(T)]
    own = prob.add_variable_dicts("own", keys, cat="Binary")
    xi = prob.add_variable_dicts("xi", keys, cat="Binary")
    cap = prob.add_variable_dicts("cap", keys, cat="Binary")
    buy = prob.add_variable_dicts("buy", keys, cat="Binary")
    sell = prob.add_variable_dicts("sell", keys, cat="Binary")
    ft = prob.add_variable_dicts("ft", list(range(T)), lowBound=0, upBound=ft_cap, cat="Integer")
    hit = prob.add_variable_dicts(
        "hit", list(range(T)), lowBound=0, upBound=MAX_MOVES_PER_GW, cat="Integer"
    )

    # --- squad continuity, and the no-buy-back rule that keeps sale prices scalar
    for i in ids:
        for t in range(T):
            prior = 1 if (t == 0 and i in owned) else (own[(i, t - 1)] if t else 0)
            prob += own[(i, t)] == prior + buy[(i, t)] - sell[(i, t)]
            prob += buy[(i, t)] + sell[(i, t)] <= 1
        prob += pulp.lpSum(buy[(i, t)] for t in range(T)) <= (0 if i in owned else 1)
        prob += pulp.lpSum(sell[(i, t)] for t in range(T)) <= 1

    # --- manager overlay (CLAUDE.md rule 4): lock = refuse to sell for the whole
    # path; ban = refuse to own it in any gameweek of the path.
    for i in lock:
        if i in price:
            for t in range(T):
                prob += own[(i, t)] == 1
    for i in ban:
        if i in price:
            for t in range(T):
                prob += own[(i, t)] == 0

    for t in range(T):
        # --- squad shape and club cap, every gameweek
        prob += pulp.lpSum(own[(i, t)] for i in ids) == sum(shape.values())
        for position in POSITIONS:
            prob += (
                pulp.lpSum(own[(i, t)] for i in ids if pos[i] == position) == shape[position]
            )
        for team in set(club.values()):
            prob += pulp.lpSum(own[(i, t)] for i in ids if club[i] == team) <= max_per_club

        # --- XI formation and captain, every gameweek
        prob += pulp.lpSum(xi[(i, t)] for i in ids) == int(lineup["starting"])
        prob += (
            pulp.lpSum(xi[(i, t)] for i in ids if pos[i] == "GKP")
            == int(lineup["min_goalkeepers"])
        )
        prob += (
            pulp.lpSum(xi[(i, t)] for i in ids if pos[i] == "DEF") >= int(lineup["min_defenders"])
        )
        prob += (
            pulp.lpSum(xi[(i, t)] for i in ids if pos[i] == "MID")
            >= int(lineup["min_midfielders"])
        )
        prob += (
            pulp.lpSum(xi[(i, t)] for i in ids if pos[i] == "FWD") >= int(lineup["min_forwards"])
        )
        prob += pulp.lpSum(cap[(i, t)] for i in ids) == 1
        for i in ids:
            prob += xi[(i, t)] <= own[(i, t)]
            prob += cap[(i, t)] <= xi[(i, t)]

        # --- free-transfer accumulation with the banking cap (the whole point)
        moves = pulp.lpSum(buy[(i, t)] for i in ids)
        prob += moves <= MAX_MOVES_PER_GW
        if t == 0:
            prob += ft[0] == min(int(current.free_transfers), ft_cap)
        else:
            prev_moves = pulp.lpSum(buy[(i, t - 1)] for i in ids)
            prob += ft[t] <= ft[t - 1] - prev_moves + hit[t - 1] + ft_per_gw
        prob += hit[t] >= moves - ft[t]

        # --- bank: cumulative, so a sale in GW t funds a buy in GW t+2
        prob += (
            current.bank
            + pulp.lpSum(
                sale[i] * sell[(i, u)] - price[i] * buy[(i, u)]
                for i in ids
                for u in range(t + 1)
            )
            >= 0
        )

    if first_move == "roll":
        prob += pulp.lpSum(buy[(i, 0)] for i in ids) == 0
    elif first_move == "move":
        prob += pulp.lpSum(buy[(i, 0)] for i in ids) >= 1
    if not allow_first_hit:
        prob += hit[0] == 0

    # Points are DECAYED (comparable with milp's xpts_horizon); hit costs are NOT
    # (a -4 is certain, a future gain is a discounted guess). The FT term is a
    # tie-break hair, not an economic value — see FT_TIEBREAK_BONUS.
    prob += (
        pulp.lpSum(
            weight[t]
            * (
                pulp.lpSum(xi[(i, t)] * score[(i, t)] for i in ids)
                + pulp.lpSum(cap[(i, t)] * score[(i, t)] for i in ids)
                + BENCH_WEIGHT
                * pulp.lpSum((own[(i, t)] - xi[(i, t)]) * score[(i, t)] for i in ids)
            )
            for t in range(T)
        )
        - hit_cost * pulp.lpSum(hit[t] for t in range(T))
        + FT_TIEBREAK_BONUS * pulp.lpSum(ft[t] for t in range(T))
    )

    status = pulp.LpStatus[prob.solve(_solver())]
    objective = prob.objective.value()
    if status not in ("Optimal", "Not Solved", "Undefined") or objective is None:
        raise InfeasibleError(f"solver status: {status}")
    truncated = status != "Optimal"

    def on(var: pulp.LpVariable) -> bool:
        return (var.value() or 0.0) > 0.5

    moves_out: list[PlannedMove] = []
    bank = int(current.bank)
    for t, (gw, col) in enumerate(periods):
        bought = sorted(i for i in ids if on(buy[(i, t)]))
        sold = sorted(i for i in ids if on(sell[(i, t)]))
        bank += sum(sale[i] for i in sold) - sum(price[i] for i in bought)
        ft_before = round(ft[t].value() or 0.0)
        n_hits = round(hit[t].value() or 0.0)
        ft_after = max(0, ft_before - len(bought) + n_hits)
        started = [i for i in ids if on(xi[(i, t)])]
        captain = next(i for i in ids if on(cap[(i, t)]))
        moves_out.append(
            PlannedMove(
                gw=gw,
                out_ids=tuple(sold),
                in_ids=tuple(bought),
                out_names=tuple(name[i] for i in sold),
                in_names=tuple(name[i] for i in bought),
                hits=n_hits,
                free_transfers_before=ft_before,
                free_transfers_after=ft_after,
                free_transfers_next=min(ft_cap, ft_after + ft_per_gw),
                bank_after=bank,
                gw_xpts=round(
                    sum(float(by_id.loc[i, col]) for i in started)
                    + float(by_id.loc[captain, col]),
                    2,
                ),
            )
        )
    return _PathSolution(
        moves=tuple(moves_out), objective=round(float(objective), 3), truncated=truncated
    )


# --------------------------------------------------------------------- advice


def _rationale(path_gws: tuple[int, ...], this_week: PlannedMove,
               forward: tuple[PlannedMove, ...], roll_gain: float | None,
               verdict: str, hit_gate: str, pool_size: int) -> str:
    """The paste-into-a-memo paragraph. States the call, prices the alternative,
    then lists the forward steps — the same shape the hand-written plan.md used."""
    span = f"GW{path_gws[0]}" if len(path_gws) == 1 else f"GW{path_gws[0]}-{path_gws[-1]}"
    head = (
        f"GW{this_week.gw} ROLL: bank the free transfer"
        f" ({this_week.free_transfers_before} -> {this_week.free_transfers_next} FT)."
        if verdict == "roll"
        else f"GW{this_week.gw} MOVE: {this_week.summary}."
    )
    if roll_gain is None:
        price_line = (
            " No legal alternative to compare against (the other branch was infeasible)."
        )
    elif abs(roll_gain) < ROLL_DECISIVE_EDGE:
        price_line = (
            f" Roll-vs-move is within noise ({roll_gain:+.2f} pts over {span},"
            f" under the {ROLL_DECISIVE_EDGE} decisive floor) — treat this as a free"
            " choice and let the manager overlay decide."
        )
    elif verdict == "roll":
        price_line = (
            f" Banking the free transfer is worth {roll_gain:+.2f} pts over {span}"
            " versus the best move available now."
        )
    else:
        price_line = (
            f" Moving now beats banking by {-roll_gain:+.2f} pts over {span}"
            " — the free transfer buys more today than it unlocks later."
        )
    queued = [m for m in forward if not m.is_roll]
    steps = (
        " Planned path: " + "; ".join(m.describe() for m in queued) + "."
        if queued
        else " No further moves planned inside the horizon."
    )
    gate = f" Hit gate: {hit_gate}." if hit_gate != "n/a" else ""
    tail = (
        f" Derived from a {len(path_gws)}-GW multi-period solve over a {pool_size}-player"
        " pool; forward steps are provisional and re-solved every deadline. A CANDIDATE,"
        " not an order (CLAUDE.md rule 4)."
    )
    return head + price_line + steps + gate + tail


def _caveats(periods: list[tuple[int, str]], truncated: bool) -> tuple[str, ...]:
    out = [
        "prices static: no price rises/falls modelled inside the horizon",
        "no buy-back: a sold player cannot be re-bought inside the path",
        "no chips: wildcard/free-hit timing is chip_timing.advise's call",
        "minutes/news frozen at solve time — forward steps are provisional",
        (
            f"pool pruned to the top {POOL_TOP_N_PER_POSITION}/position by points "
            f"+ {POOL_TOP_N_VALUE_PER_POSITION}/position by value, plus everything owned"
        ),
        "bench valued at the flat milp.BENCH_WEIGHT fraction; no vice, no autosub model",
    ]
    if periods and periods[0][0] == 0:
        out.append(
            "no per-GW columns found: collapsed to a single xpts_horizon period "
            "(the path is a single-period answer)"
        )
    elif len(periods) == 1:
        out.append("only one per-GW column: single-period answer, no forward path")
    if truncated:
        out.append(
            f"a solve hit the {SOLVER_TIME_LIMIT_SECONDS}s limit — best incumbent, "
            "not proven optimal"
        )
    return tuple(out)


def plan_transfer_path(
    projections: pd.DataFrame,
    rules: Ruleset | None = None,
    current: CurrentSquad | None = None,
    horizon: int | None = None,
    allow_unverified: bool = False,
    lock: frozenset[int] = frozenset(),
    ban: frozenset[int] = frozenset(),
    pool: pd.DataFrame | None = None,
) -> TransferPath:
    """Plan WHICH transfers to make in WHICH gameweek — the advisory entry point.

    `current` is the squad we hold (buy costs, bank, free transfers) exactly as
    `milp.optimize` takes it. The solve runs three times at most:

      1. the free path (what the model wants);
      2. if it takes a hit this week, the best path with NO hit this week — the
         marginal net gain per hit is checked against `policies.hit_ev_threshold`
         and a failing hit is STRIPPED, mirroring `simulate.decide_transfers` so
         the two layers can never disagree about what a hit is worth;
      3. the opposite branch of the roll/move question, to price banking.

    Returns a TransferPath. Like the rest of `optimize/`, it refuses to run
    against an unverified ruleset unless `allow_unverified=True`.
    """
    rules = rules or Ruleset.load()
    if not rules.is_verified() and not allow_unverified:
        raise RulesetUnverifiedError(
            "ruleset has unverified sections "
            f"{rules.unverified_sections()} — verify vs the official site at season "
            "launch, or pass allow_unverified=True for a dry run and label the output"
        )
    if current is None:
        raise ValueError("plan_transfer_path needs the current squad (CurrentSquad)")
    players = projections.drop_duplicates(subset="id")
    missing = set(current.buy_costs) - {int(i) for i in players["id"]}
    if missing:
        raise ValueError(f"owned players missing from projections table: {sorted(missing)}")

    periods = horizon_columns(players, horizon)
    if pool is None:
        pool = prune_pool(players, set(current.buy_costs), keep=lock)
    pool_size = len(pool)

    base = _solve_path(pool, rules, current, periods, lock, ban)
    truncated = base.truncated

    # --- hit gate, same semantics as simulate.decide_transfers (marginal, per hit)
    hit_gate = "n/a"
    allow_first_hit = True
    if base.moves[0].hits > 0:
        nohit = _solve_path(pool, rules, current, periods, lock, ban, allow_first_hit=False)
        truncated = truncated or nohit.truncated
        threshold = float(rules.policy("hit_ev_threshold"))
        marginal = round(base.objective - nohit.objective, 2)
        if marginal < threshold * base.moves[0].hits:
            hit_gate = f"rejected: net {marginal} < {threshold}/hit"
            base, allow_first_hit = nohit, False
        else:
            hit_gate = f"kept: net {marginal} >= {threshold}/hit"

    # --- price the roll: solve whichever branch the free path did NOT take
    verdict = "roll" if base.moves[0].is_roll else "move"
    other = "move" if verdict == "roll" else "roll"
    try:
        alt = _solve_path(
            pool, rules, current, periods, lock, ban,
            first_move=other, allow_first_hit=allow_first_hit,
        )
        truncated = truncated or alt.truncated
        alt_objective: float | None = alt.objective
    except InfeasibleError:
        alt_objective = None  # e.g. nothing affordable to move into
    roll_objective = base.objective if verdict == "roll" else alt_objective
    move_objective = alt_objective if verdict == "roll" else base.objective
    roll_gain = (
        None
        if roll_objective is None or move_objective is None
        else round(roll_objective - move_objective, 2)
    )

    this_week, forward = base.moves[0], tuple(base.moves[1:])
    gws = tuple(gw for gw, _col in periods)
    return TransferPath(
        gws=gws,
        this_week=this_week,
        forward=forward,
        objective=base.objective,
        roll_objective=roll_objective,
        move_objective=move_objective,
        roll_gain=roll_gain,
        verdict=verdict,
        hit_gate=hit_gate,
        pool_size=pool_size,
        truncated=truncated,
        rationale=_rationale(gws, this_week, forward, roll_gain, verdict, hit_gate, pool_size),
        caveats=_caveats(periods, truncated),
    )

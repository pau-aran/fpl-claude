"""Spend-vs-EV frontier for an initial build: what does the last million buy?

The optimizer spends the whole budget because the budget is there, not because
the tail of it is worth anything. This sweeps a cap on SPEND (the money is not
lost — the remainder banks) and prints what each step down costs in decayed
horizon points and in Gameweek-1 XI points, so the manager can price the
trade-off instead of assuming it.

Read the output as a frontier, not a ranking: the right cap is the knee, the
point past which each further million starts costing real points. Unspent money
is an option on the next few deadlines — worth most exactly when the squad is
built on a forecast that might need reversing.

CLI:  python notebooks/gw01_spend_frontier.py --projections PATH
          [--ban 61,68,...] [--from 100.0] [--to 92.0] [--step 0.5]
"""

from __future__ import annotations

import argparse
from itertools import pairwise

import pandas as pd

from fpl_claude.optimize.milp import optimize
from fpl_claude.rules.engine import Ruleset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projections", required=True)
    parser.add_argument("--ban", default="", help="comma-separated player ids to exclude")
    parser.add_argument("--lock", default="", help="comma-separated player ids to force in")
    parser.add_argument("--season", default="2026-27")
    parser.add_argument("--from", dest="hi", type=float, default=100.0)
    parser.add_argument("--to", dest="lo", type=float, default=92.0)
    parser.add_argument("--step", type=float, default=0.5)
    args = parser.parse_args()

    rules = Ruleset.load(args.season)
    proj = pd.read_csv(args.projections)
    ban = frozenset(int(x) for x in args.ban.split(",") if x.strip())
    lock = frozenset(int(x) for x in args.lock.split(",") if x.strip())
    by_id = proj.set_index("id")

    caps = []
    cap = args.hi
    while cap >= args.lo - 1e-9:
        caps.append(round(cap, 1))
        cap -= args.step

    baseline = None
    rows = []
    squads: dict[float, list[int]] = {}
    for cap in caps:
        result = optimize(proj, rules, ban=ban, lock=lock, budget=round(cap * 10))
        xi_gw1 = sum(float(by_id.loc[i, "xpts_gw1"]) for i in result.xi)
        xi_gw1 += float(by_id.loc[result.captain, "xpts_gw1"])
        # The objective also prices the bench at 10% — and at a season open the
        # bench is four players the model cannot tell apart (every one of them
        # `neutral` confidence, all projected at the positional replacement
        # level). So the XI-only horizon is reported beside it: that is the part
        # of the frontier made of evidence rather than of a modelling artefact.
        xi_horizon = sum(float(by_id.loc[i, "xpts_horizon"]) for i in result.xi)
        xi_horizon += float(by_id.loc[result.captain, "xpts_horizon"])
        if baseline is None:
            baseline = (result.objective, xi_gw1, xi_horizon)
        squads[cap] = sorted(result.squad)
        rows.append(
            {
                "cap": cap,
                "spend": round(result.cost / 10, 1),
                "bank": round((rules.raw["budget"]["initial"] * 10 - result.cost) / 10, 1),
                "objective": round(result.objective, 3),
                "d_obj": round(result.objective - baseline[0], 3),
                "xi_gw1": round(xi_gw1, 2),
                "d_gw1": round(xi_gw1 - baseline[1], 2),
                "xi_horizon": round(xi_horizon, 2),
                "d_xi_h": round(xi_horizon - baseline[2], 2),
                "chg": len(set(squads[caps[0]]) - set(squads[cap])),
            }
        )

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    print()
    print("Points given up per £1.0m of bank (marginal, on the decayed 5-GW objective):")
    for prev, cur in pairwise(rows):
        step = prev["cap"] - cur["cap"]
        if step:
            per_m = (prev["objective"] - cur["objective"]) / step
            print(f"  £{prev['cap']}m -> £{cur['cap']}m: {per_m:6.3f} objective pts per £1.0m")

    full = set(squads[caps[0]])
    print()
    for cap in caps:
        out = sorted(full - set(squads[cap]))
        into = sorted(set(squads[cap]) - full)
        if not out:
            continue
        names_out = ", ".join(str(by_id.loc[i, "web_name"]) for i in out)
        names_in = ", ".join(str(by_id.loc[i, "web_name"]) for i in into)
        print(f"cap £{cap}m: out [{names_out}] -> in [{names_in}]")


if __name__ == "__main__":
    main()

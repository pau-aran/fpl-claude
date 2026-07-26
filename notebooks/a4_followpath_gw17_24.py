"""A4 acceptance run: replay GW17-24 with the multi-period planner DECIDING.

The hand-written FT-banking path over the AFCON window (GW17-24) entered at
+135 vs the average manager and exited at +191 — net +56 of edge, 439 actual
points. A4 (`optimize/transfer_path.py`) encodes that logic as a model; this
script asks the only question that matters before trusting it: **starting from
the identical GW17 state, with identical projections, overlays and actuals,
how many points does the model-driven path score on its own?**

Two runs, so the per-move edge floor's contribution is measured, not asserted:

  floored     follow_path=True with MOVE_EDGE_FLOOR (the shipped default)
  unfloored   follow_path=True with move_edge_floor=None (the churny planner
              that was NOT trusted — the A4 review's Saliba->Raya concern)

Both runs are PURE MODEL: the committed news overlays are applied (both worlds
saw the same news — they are inputs, not decisions), but no manager locks,
bans, transfer caps, captain overrides or chips. The committed 439 was earned
WITH those overlays, so the gap between a run and 439 is the value of the
manager layer on top of that run's transfer policy.

The entering state is RECONSTRUCTED from committed artifacts only (gw16
players CSV for the squad, the gw01-16 CSV sequence for buy costs, the gw16
memo for bank/FT/totals) and cross-checked against the committed post-GW24
state.json before anything runs — see `reconstruct_gw17_state`.

Usage (from the repo root, ~10-20 min):
    python notebooks/a4_followpath_gw17_24.py [--data db/vaastav]
        [--out db/backtest/a4-followpath]

Writes per-run memos/state under --out (gitignored scratch) and prints the
comparison table. The written verdict lives in
reports/backtest/2025-26/a4-followpath-verdict.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fpl_claude.backtest import simulate
from fpl_claude.backtest.data import SeasonStore
from fpl_claude.backtest.overlays import availability_overlays, merge
from fpl_claude.backtest.simulate import SquadState, run_gameweek
from fpl_claude.console import enable_utf8_output
from fpl_claude.optimize import transfer_path
from fpl_claude.rules.engine import Ruleset

REPORTS = ROOT / "reports" / "backtest" / "2025-26"
WINDOW = range(17, 25)  # GW17..24
HAND_WRITTEN_ACTUAL = 439  # the committed GW17-24 total (sum of the 8 memos)
FIELD_AVERAGE = 379  # sum of the official GW averages over the window


def _squad_ids(gw: int) -> list[int]:
    return pd.read_csv(REPORTS / f"gw{gw:02d}_players.csv")["id"].astype(int).tolist()


def _prices(gw: int) -> dict[int, int]:
    df = pd.read_csv(REPORTS / f"gw{gw:02d}_players.csv")
    return {int(i): round(float(p) * 10) for i, p in zip(df["id"], df["price"])}


def reconstruct_gw17_state() -> SquadState:
    """The squad state ENTERING GW17, from committed artifacts only.

    Buy costs: walk the gw01-16 players CSVs in order; a player's buy cost is
    his price in the first GW he (re)appears — exactly what apply_transfers
    recorded at the time. Bank/FT/totals: the gw16 memo's own lines.
    """
    buy_costs: dict[int, int] = {}
    held: set[int] = set()
    for gw in range(1, 17):
        ids = set(_squad_ids(gw))
        prices = _prices(gw)
        for pid in ids - held:  # bought (or initial build) at this GW's price
            buy_costs[pid] = prices[pid]
        for pid in held - ids:
            buy_costs.pop(pid)
        held = ids

    memo = (REPORTS / "gw16.md").read_text(encoding="utf-8")
    bank = round(10 * float(re.search(r"Bank after moves: £([\d.]+)m", memo).group(1)))
    fts = int(re.search(r"free transfers left for next GW: (\d+)", memo).group(1))
    points = int(re.search(r"Season total: \*\*(\d+)\*\*", memo).group(1))
    hits = int(re.search(r"hits taken: (\d+)", memo).group(1))

    state = SquadState(
        buy_costs=buy_costs, bank=bank, free_transfers=fts,
        points_total=points, hits_total=hits, chips_used=[],
    )
    _validate(state)
    return state


def _validate(state: SquadState) -> None:
    """Cross-check the reconstruction against the committed post-GW24 state:
    any player held from GW16 through GW24 untraded must carry the same buy
    cost there as we reconstructed here. A mismatch means the walk is wrong."""
    committed = json.loads((REPORTS / "state.json").read_text())["buy_costs"]
    held_throughout = set(state.buy_costs)
    for gw in WINDOW:
        held_throughout &= set(_squad_ids(gw))
    mismatches = {
        pid: (state.buy_costs[pid], int(committed[str(pid)]))
        for pid in held_throughout
        if int(committed.get(str(pid), -1)) != state.buy_costs[pid]
    }
    if mismatches:
        raise AssertionError(f"buy-cost reconstruction mismatches: {mismatches}")
    if len(state.buy_costs) != 15:
        raise AssertionError(f"reconstructed squad has {len(state.buy_costs)} players")
    print(
        f"reconstruction validated: 15 players, bank £{state.bank / 10:.1f}m, "
        f"{state.free_transfers} FT, {state.points_total} pts, "
        f"{len(held_throughout)} buy-costs cross-checked vs committed state.json"
    )


def replay(label: str, store: SeasonStore, rules: Ruleset, out_dir: Path,
           edge_floor: float | None) -> dict:
    """One GW17-24 run with the planner deciding every transfer."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # The floor is plan_transfer_path's default argument; decide_transfers calls
    # it without naming it, so the experiment switches it at the module level.
    plan = transfer_path.plan_transfer_path

    def patched(projections, rules=None, current=None, **kw):
        kw.setdefault("move_edge_floor", edge_floor)
        return plan(projections, rules, current, **kw)

    simulate.plan_transfer_path = patched
    try:
        state = reconstruct_gw17_state()
        rows = []
        for gw in WINDOW:
            overlays_path = REPORTS / "overlays" / f"gw{gw:02d}.json"
            hand = {
                int(k): v
                for k, v in json.loads(overlays_path.read_text(encoding="utf-8")).items()
            }
            overlays = merge(availability_overlays(store, gw), hand)
            result, state = run_gameweek(
                store, gw, rules, state, overlays=overlays, decision=None,
                follow_path=True,
            )
            moves = ", ".join(
                f"{o}->{i}" for o, i in result.transfers
            ) or "roll"
            rows.append(
                {
                    "gw": gw, "moves": moves, "hits": result.hits,
                    "predicted": result.predicted_xi_pts, "actual": result.actual_pts,
                }
            )
            result.player_rows.to_csv(out_dir / f"gw{gw:02d}_players.csv", index=False)
            print(f"[{label}] GW{gw}: {moves} | hits {result.hits} | actual {result.actual_pts}")
        table = pd.DataFrame(rows)
        summary = {
            "label": label,
            "edge_floor": edge_floor if edge_floor is not None else "off",
            "total_actual": int(table["actual"].sum()),
            "total_hits": int(table["hits"].sum()),
            "n_transfers": int(sum(len(r["moves"].split(",")) for r in rows
                                   if r["moves"] != "roll")),
            "per_gw": rows,
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
        return summary
    finally:
        simulate.plan_transfer_path = plan


def main() -> None:
    enable_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT / "db" / "vaastav"))
    parser.add_argument("--out", default=str(ROOT / "db" / "backtest" / "a4-followpath"))
    args = parser.parse_args()

    store = SeasonStore(Path(args.data), season="2025-26")
    rules = Ruleset.load("2025-26")
    out = Path(args.out)

    results = [
        replay("floored", store, rules, out / "floored",
               transfer_path.MOVE_EDGE_FLOOR),
        replay("unfloored", store, rules, out / "unfloored", None),
    ]

    print("\n=== A4 follow-path acceptance: GW17-24, identical entry state ===")
    print(f"{'run':<24}{'actual':>8}{'transfers':>11}{'hits':>6}{'vs hand':>9}{'vs field':>10}")
    hand = HAND_WRITTEN_ACTUAL
    print(f"{'hand-written (committed)':<24}{hand:>8}{'—':>11}{1:>6}{0:>+9}{hand - FIELD_AVERAGE:>+10}")
    for r in results:
        print(
            f"{r['label'] + ' follow_path':<24}{r['total_actual']:>8}"
            f"{r['n_transfers']:>11}{r['total_hits']:>6}"
            f"{r['total_actual'] - hand:>+9}{r['total_actual'] - FIELD_AVERAGE:>+10}"
        )


if __name__ == "__main__":
    main()

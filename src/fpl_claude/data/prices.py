"""Price tracking and the price-change radar.

Prices matter twice in FPL: squad value (banking early £0.1 rises compounds into
budget headroom by mid-season) and timing (buy before the rise, sell before the
fall — but never let a price move force a football decision; that's the tail
wagging the dog and every memo that acts on price says so explicitly).

Two data products, both from data we already snapshot daily:

  price history   `now_cost` per player across snapshot dates (db/raw/) —
                  actual rises/falls since the previous snapshot
  transfer        net transfers this event scaled by current owners — a
  pressure        ranking signal for who is CLOSE to a move. FPL's real
                  threshold algorithm is secret; this is a heuristic ranker,
                  cross-checked against FPL Statistics (sources.yaml, tier 2),
                  never a prediction we publish as fact.

Flagged players (status != 'a') are marked: FPL usually freezes or dampens
their price movement, so pressure on them overstates the risk.

CLI:  python -m fpl_claude.data.prices [--from-snapshot YYYY-MM-DD] [--top N]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..console import enable_utf8_output
from .fpl_api import RAW_DIR, get_bootstrap

HISTORY_COLUMNS = ["id", "web_name", "now_cost", "cost_change_event", "status"]


def price_history(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """(snapshot_date, id, web_name, now_cost, ...) across all snapshots."""
    frames = []
    for day_dir in sorted(raw_dir.iterdir()) if raw_dir.exists() else []:
        bootstrap_file = day_dir / "bootstrap.json"
        if not (day_dir.is_dir() and bootstrap_file.exists()):
            continue
        elements = json.loads(bootstrap_file.read_text())["elements"]
        frame = pd.DataFrame(elements)[HISTORY_COLUMNS].copy()
        frame.insert(0, "snapshot_date", day_dir.name)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["snapshot_date", *HISTORY_COLUMNS])
    return pd.concat(frames, ignore_index=True)


def latest_changes(history: pd.DataFrame) -> pd.DataFrame:
    """Players whose price moved between the two most recent snapshots.

    Returns (id, web_name, prev_cost, now_cost, delta) in API tenths of £m,
    empty if fewer than two snapshot dates exist.
    """
    dates = sorted(history["snapshot_date"].unique())
    if len(dates) < 2:
        return pd.DataFrame(columns=["id", "web_name", "prev_cost", "now_cost", "delta"])
    prev = history[history["snapshot_date"] == dates[-2]].set_index("id")
    curr = history[history["snapshot_date"] == dates[-1]].set_index("id")
    joined = curr.join(prev[["now_cost"]], rsuffix="_prev", how="inner")
    moved = joined[joined["now_cost"] != joined["now_cost_prev"]]
    return (
        pd.DataFrame(
            {
                "id": moved.index,
                "web_name": moved["web_name"].values,
                "prev_cost": moved["now_cost_prev"].values,
                "now_cost": moved["now_cost"].values,
                "delta": (moved["now_cost"] - moved["now_cost_prev"]).values,
            }
        )
        .sort_values("delta", ascending=False)
        .reset_index(drop=True)
    )


def transfer_pressure(bootstrap: dict) -> pd.DataFrame:
    """Net event transfers scaled by estimated owner count, ranked.

    pressure > 0 → rise-side, < 0 → fall-side. Magnitude is only a ranking:
    the actual thresholds are FPL's secret and vary through the season.
    """
    total_players = int(bootstrap.get("total_players") or 0)
    rows = []
    for p in bootstrap["elements"]:
        ownership = float(p.get("selected_by_percent") or 0)
        owners = max(1.0, ownership / 100.0 * total_players) if total_players else 1.0
        net = int(p.get("transfers_in_event") or 0) - int(p.get("transfers_out_event") or 0)
        rows.append(
            {
                "id": int(p["id"]),
                "web_name": p["web_name"],
                "price": p["now_cost"] / 10.0,
                "ownership_pct": ownership,
                "net_transfers_event": net,
                "pressure": net / owners if total_players else 0.0,
                "cost_change_event": int(p.get("cost_change_event") or 0),
                "flagged": p.get("status", "a") != "a",
            }
        )
    return (
        pd.DataFrame(rows).sort_values("pressure", ascending=False).reset_index(drop=True)
    )


def radar(bootstrap: dict, top_n: int = 15) -> dict[str, pd.DataFrame]:
    """Top rise-side and fall-side candidates by transfer pressure."""
    pressure = transfer_pressure(bootstrap)
    return {
        "risers": pressure.head(top_n).reset_index(drop=True),
        "fallers": pressure.tail(top_n).iloc[::-1].reset_index(drop=True),
    }


def main() -> None:
    enable_utf8_output()  # price moves print "4.5 → 4.6"; cp1252 aborts on it
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", help="db/raw/ date dir instead of live API")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    if args.from_snapshot:
        bootstrap = json.loads((RAW_DIR / args.from_snapshot / "bootstrap.json").read_text())
    else:
        bootstrap = get_bootstrap()

    boards = radar(bootstrap, args.top)
    for side in ("risers", "fallers"):
        print(f"\n== {side} (transfer pressure — heuristic ranking) ==")
        print(boards[side].to_string(index=False))

    changes = latest_changes(price_history())
    if not changes.empty:
        print("\n== actual moves since previous snapshot ==")
        print(changes.to_string(index=False))


if __name__ == "__main__":
    main()

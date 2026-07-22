"""Price tracking, transfer-pressure radar, and sell-price rule — offline."""

from __future__ import annotations

import json
from pathlib import Path

from fpl_claude.data import prices
from fpl_claude.rules.engine import Ruleset


def _element(pid, name, cost, tin=0, tout=0, owned="10.0", status="a", change=0):
    return {
        "id": pid, "web_name": name, "now_cost": cost, "status": status,
        "cost_change_event": change, "selected_by_percent": owned,
        "transfers_in_event": tin, "transfers_out_event": tout,
    }


def _write_snapshot(raw_dir: Path, day: str, elements: list[dict]) -> None:
    day_dir = raw_dir / day
    day_dir.mkdir(parents=True)
    (day_dir / "bootstrap.json").write_text(
        json.dumps({"elements": elements, "teams": [], "events": [], "total_players": 1000000})
    )


def test_price_history_and_latest_changes(tmp_path: Path):
    _write_snapshot(tmp_path, "2026-08-01", [
        _element(1, "Riser", 55), _element(2, "Faller", 80), _element(3, "Flat", 45),
    ])
    _write_snapshot(tmp_path, "2026-08-02", [
        _element(1, "Riser", 56, change=1), _element(2, "Faller", 79, change=-1),
        _element(3, "Flat", 45),
    ])

    history = prices.price_history(tmp_path)
    assert len(history) == 6
    changes = prices.latest_changes(history)
    assert list(changes["web_name"]) == ["Riser", "Faller"]  # sorted by delta desc
    assert list(changes["delta"]) == [1, -1]


def test_latest_changes_needs_two_snapshots(tmp_path: Path):
    _write_snapshot(tmp_path, "2026-08-01", [_element(1, "Solo", 50)])
    assert prices.latest_changes(prices.price_history(tmp_path)).empty
    assert prices.latest_changes(prices.price_history(tmp_path / "nowhere")).empty


def test_transfer_pressure_ranks_and_flags():
    bootstrap = {
        "total_players": 1_000_000,
        "elements": [
            # 100k owners, +50k net -> pressure 0.5 (hot riser)
            _element(1, "Hot", 55, tin=60_000, tout=10_000, owned="10.0"),
            # 500k owners, +50k net -> pressure 0.1 (same net, cooler)
            _element(2, "Template", 120, tin=55_000, tout=5_000, owned="50.0"),
            # exodus: -30k on 50k owners -> pressure -0.6
            _element(3, "Panic", 75, tin=0, tout=30_000, owned="5.0", status="i"),
        ],
    }
    pressure = prices.transfer_pressure(bootstrap).set_index("web_name")
    assert pressure.loc["Hot", "pressure"] > pressure.loc["Template", "pressure"] > 0
    assert pressure.loc["Panic", "pressure"] < 0
    assert bool(pressure.loc["Panic", "flagged"])  # price-frozen candidate

    boards = prices.radar(bootstrap, top_n=1)
    assert boards["risers"].iloc[0]["web_name"] == "Hot"
    assert boards["fallers"].iloc[0]["web_name"] == "Panic"


def test_sell_price_half_profit_rounded_down():
    rules = Ruleset.load("2026-27")
    assert rules.sell_price(55, 58) == 56   # +0.3 -> keep 0.1
    assert rules.sell_price(55, 57) == 56   # +0.2 -> keep 0.1
    assert rules.sell_price(55, 56) == 55   # +0.1 -> rounds away
    assert rules.sell_price(55, 55) == 55   # unchanged
    assert rules.sell_price(55, 52) == 52   # losses in full

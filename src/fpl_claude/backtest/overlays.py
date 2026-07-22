"""Point-in-time availability proxies for season replays.

The vaastav archive has no historical injury flags, so a replayed season would
happily keep projecting minutes for players every real manager knew were out
(injured, on strike, sold abroad). What a manager COULD see at any deadline
without any news source is the recent minutes record itself — a nailed player
who suddenly logs consecutive zero-minute gameweeks while his team plays is
visibly unavailable, whatever the reason.

This module turns that public signal into minutes-model overlays (the same
mechanism the live news-sweep uses), each with a written reason. Thresholds are
deliberately conservative: one blank GW is rotation noise mid-season, but at
GW2 it is the only evidence that exists, so it bites harder there.

Hand-written news overlays (e.g. pre-GW1 transfer/strike news that was public
before the deadline) can be merged on top via `merge` — hand-written wins.
"""

from __future__ import annotations

from typing import Any

from .data import SeasonStore

LOOKBACK_GWS = 3
SHARE_TWO_BLANKS = 0.12
SHARE_THREE_BLANKS = 0.04
SHARE_ONE_BLANK_EARLY = 0.30  # only applied while one GW is ALL the evidence


def availability_overlays(store: SeasonStore, gw: int) -> dict[int, dict[str, Any]]:
    """Overlays for players with consecutive zero-minute GWs before `gw`."""
    if gw < 2:
        return {}
    window = store.merged[
        (store.merged["GW"] >= gw - LOOKBACK_GWS) & (store.merged["GW"] < gw)
    ]
    minutes_by_gw = window.groupby(["element", "GW"])["minutes"].sum()

    overlays: dict[int, dict[str, Any]] = {}
    for pid in window["element"].unique():
        per_gw = minutes_by_gw.loc[int(pid)].sort_index(ascending=False)
        blanks = 0
        for m in per_gw:  # consecutive zero-minute GWs, most recent first
            if m > 0:
                break
            blanks += 1
        if blanks == 0:
            continue
        if blanks >= 3:
            share, label = SHARE_THREE_BLANKS, f"{blanks} straight blank GWs"
        elif blanks >= 2:
            share, label = SHARE_TWO_BLANKS, "2 straight blank GWs"
        elif gw == 2:
            share, label = SHARE_ONE_BLANK_EARLY, "blank in GW1 (only GW played)"
        else:
            continue
        overlays[int(pid)] = {
            "start_share": share,
            "reason": f"availability proxy: {label} while team played",
        }
    return overlays


def merge(
    base: dict[int, dict[str, Any]], override: dict[int, dict[str, Any]] | None
) -> dict[int, dict[str, Any]]:
    """Layer hand-written overlays over generated ones (hand-written wins)."""
    merged = dict(base)
    if override:
        merged.update(override)
    return merged

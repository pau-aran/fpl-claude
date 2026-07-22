"""Per-90 player event rates from FPL bootstrap data, with prior blending.

The rates layer feeds the scoring map: xG/xA per 90 (finishing-independent
underlying numbers), saves per 90 (GK), defensive contributions per 90 (the
2025/26 scoring category), and a bonus-per-90 proxy.

Early season the current-season sample is tiny (pre-season it is zero), so
rates are shrunk toward a prior — typically last season's final bootstrap
snapshot (`from_bootstrap` on that file). Players without a prior (new signings)
keep their small-sample current rates and are flagged low-sample so the skills
know the projection is soft there.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# Sample size (in full matches) at which current-season rates get full weight.
FULL_WEIGHT_MATCHES = 6

RATE_COLUMNS = ["xg90", "xa90", "saves90", "dc90", "bonus90"]


def _num(value: Any) -> float:
    """FPL API numerics arrive as strings ('0.45') or None."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _per90(total: Any, minutes: int) -> float:
    return _num(total) * 90.0 / minutes if minutes > 0 else 0.0


def from_bootstrap(bootstrap: dict[str, Any]) -> pd.DataFrame:
    """Per-90 rates for every player from one bootstrap payload."""
    rows = []
    for p in bootstrap["elements"]:
        minutes = int(p.get("minutes") or 0)
        rows.append(
            {
                "id": int(p["id"]),
                "minutes_sample": minutes,
                "xg90": _per90(p.get("expected_goals"), minutes),
                "xa90": _per90(p.get("expected_assists"), minutes),
                "saves90": _per90(p.get("saves"), minutes),
                # defensive_contribution: added to the API for 2025/26; absent
                # (0) in older snapshots — the scoring map then yields 0 pts.
                "dc90": _per90(p.get("defensive_contribution"), minutes),
                "bonus90": _per90(p.get("bonus"), minutes),
            }
        )
    return pd.DataFrame(rows)


def blend(current: pd.DataFrame, prior: pd.DataFrame | None) -> pd.DataFrame:
    """Shrink current-season rates toward prior rates by sample size.

    weight = min(1, current_minutes / (FULL_WEIGHT_MATCHES * 90)); players with
    no prior row keep current rates unshrunk. Adds `low_sample` where combined
    evidence is under one full match — projections there are essentially priors
    or noise and skills must treat them as such.
    """
    if prior is None or prior.empty:
        out = current.copy()
        out["low_sample"] = out["minutes_sample"] < 90
        return out

    merged = current.merge(
        prior[["id", *RATE_COLUMNS, "minutes_sample"]],
        on="id",
        how="left",
        suffixes=("", "_prior"),
    )
    weight = (merged["minutes_sample"] / (FULL_WEIGHT_MATCHES * 90)).clip(0, 1)
    has_prior = merged["xg90_prior"].notna()
    for col in RATE_COLUMNS:
        blended = weight * merged[col] + (1 - weight) * merged[f"{col}_prior"]
        merged[col] = blended.where(has_prior, merged[col])
    merged["low_sample"] = ~has_prior & (merged["minutes_sample"] < 90)
    return merged[["id", "minutes_sample", *RATE_COLUMNS, "low_sample"]]

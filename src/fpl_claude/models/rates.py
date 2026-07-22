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

# Percentile of established players' rates (per position) that a priorless
# newcomer's rates are regressed TOWARD until he has earned full weight. A low
# percentile = "replacement level": a summer signing's two-game hot streak
# should not outrank an established player whose rate is shrunk toward his
# prior. 0.30 keeps it conservative without zeroing genuine early signal.
NEWCOMER_BASELINE_QUANTILE = 0.30

# Minimum established players at a position before its baseline is trustworthy.
MIN_BASELINE_POPULATION = 5

# Pseudo-minutes added to every per-90 denominator: shrinks tiny samples toward
# zero instead of letting them explode (a 1-minute cameo with 0.06 xG is NOT a
# 5.4 xG/90 player — backtest GW1 2025/26 captained exactly that artifact).
# A full season barely notices (~3%); a single cameo is damped ~99%.
SHRINKAGE_MINUTES = 90

RATE_COLUMNS = ["xg90", "xa90", "saves90", "dc90", "bonus90"]


def _num(value: Any) -> float:
    """FPL API numerics arrive as strings ('0.45') or None."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _per90(total: Any, minutes: int) -> float:
    return _num(total) * 90.0 / (minutes + SHRINKAGE_MINUTES) if minutes > 0 else 0.0


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
    weight_all = (current["minutes_sample"] / (FULL_WEIGHT_MATCHES * 90)).clip(0, 1)
    if prior is None or prior.empty:
        out = current.copy()
        out["low_sample"] = out["minutes_sample"] < 90
        out["has_prior"] = False
        out["evidence"] = weight_all.values
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
        if (merged[f"{col}_prior"].fillna(0) == 0).all():
            # The stat is absent from the prior era entirely (e.g. defensive
            # contribution before 2025/26): an all-zero prior column is a
            # phantom, not evidence — shrinking toward it strangles real
            # current-season signal. Keep current rates unblended.
            continue
        blended = weight * merged[col] + (1 - weight) * merged[f"{col}_prior"]
        merged[col] = blended.where(has_prior, merged[col])
    merged["low_sample"] = ~has_prior & (merged["minutes_sample"] < 90)
    merged["has_prior"] = has_prior
    # evidence = how much current-season weight the player has earned; for
    # priorless players this drives the newcomer haircut (shrink_newcomers).
    merged["evidence"] = weight
    return merged[
        ["id", "minutes_sample", *RATE_COLUMNS, "low_sample", "has_prior", "evidence"]
    ]


def shrink_newcomers(blended: pd.DataFrame, element_type: pd.Series) -> pd.DataFrame:
    """Regress priorless newcomers' rates toward a positional replacement
    baseline by their evidence weight.

    `blend` shrinks a player WITH a prior toward that prior; a player with NO
    prior (a genuine newcomer to the data — a fresh signing) has nothing to
    regress toward, so `blend` leaves his small-sample rates at full trust and
    a two-game hot streak outranks an established player's blended prior
    (knowledge.md: Ekitiké 71' vs Wood's 20-goal season). Here we regress those
    newcomers toward replacement level — a low percentile of established
    players at their position — by `evidence` (= min(1, mins/(6*90))), so the
    haircut is heaviest with the least evidence and decays to nothing once the
    newcomer has a full sample. Established (has_prior) players are untouched.

    `element_type` is a Series indexed by player id (FPL element_type 1-4).
    """
    if not {"has_prior", "evidence"}.issubset(blended.columns):
        return blended
    out = blended.copy()
    et = out["id"].map(element_type)
    established = out[out["has_prior"]]
    est_et = established["id"].map(element_type)
    baselines: dict[Any, dict[str, float]] = {}
    for pos, grp in established.groupby(est_et):
        if len(grp) >= MIN_BASELINE_POPULATION:
            baselines[pos] = {
                c: float(grp[c].quantile(NEWCOMER_BASELINE_QUANTILE)) for c in RATE_COLUMNS
            }
    newcomer = ~out["has_prior"]
    for col in RATE_COLUMNS:
        base = et.map(lambda p: baselines.get(p, {}).get(col))
        apply = newcomer & base.notna()
        if not apply.any():
            continue
        w = out.loc[apply, "evidence"]
        out.loc[apply, col] = w * out.loc[apply, col] + (1 - w) * base[apply]
    return out

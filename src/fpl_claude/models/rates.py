"""Per-90 player event rates from FPL bootstrap data, with prior blending.

The rates layer feeds the scoring map: xG/xA per 90 (finishing-independent
underlying numbers), saves per 90 (GK), defensive contributions per 90 (the
2025/26 scoring category), and a bonus-per-90 proxy.

Early season the current-season sample is tiny (pre-season it is zero), so
rates are shrunk toward a prior — typically last season's final bootstrap
snapshot (`from_bootstrap` on that file). Players without a prior (new signings)
keep their small-sample current rates and are flagged low-sample so the skills
know the projection is soft there.

A PRIOR ROW IS NOT THE SAME AS A PRIOR SAMPLE. Last season's row exists for a
player who was on loan abroad, or injured from August, or third-choice keeper —
and it is a row of zeros. Weighting that row as if it were measured turns
"we have no idea" into a confident zero (Rashford: xg90 = xa90 = 0.00 at £7.0m,
2026-07-25 run). So the prior carries its own weight, `prior_strength`, that
ramps from 0 at 0 prior minutes to 1 at PRIOR_FULL_WEIGHT_MINUTES; whatever
weight neither the current season nor the prior can account for goes to the
positional replacement baseline (`shrink_newcomers`). At full prior strength
that is arithmetically identical to the previous blend, so an established
player's rates are unchanged.
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

# Prior minutes at which last season's row counts as a full-weight prior. Below
# it the prior is *partial* evidence and the shortfall is regressed to the
# positional baseline; at 0 minutes the row carries no weight at all and the
# player is handled exactly like a priorless newcomer. 900' = ten full matches,
# the point at which a per-90 rate stops being dominated by SHRINKAGE_MINUTES.
PRIOR_FULL_WEIGHT_MINUTES = 900

# Evidence weight (current + prior) at which a player is "established": his
# rates are left alone and he is eligible to define a positional baseline.
FULL_EVIDENCE = 1.0

# One full match of current-season minutes — below it a player's own season
# tells us nothing, so `low_sample` falls back to asking the prior.
ONE_MATCH_MINUTES = 90

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
        out["low_sample"] = out["minutes_sample"] < ONE_MATCH_MINUTES
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
    prior_minutes = merged["minutes_sample_prior"].fillna(0)
    # A prior ROW is not a prior SAMPLE. Grade it by the minutes behind it: a
    # zeroed row (loan abroad, injured all season, third-choice keeper) earns
    # strength 0 and the player is handled exactly like a priorless newcomer.
    prior_strength = (prior_minutes / PRIOR_FULL_WEIGHT_MINUTES).clip(0, 1)
    prior_strength = prior_strength.where(merged["xg90_prior"].notna(), 0.0)
    has_prior = prior_strength > 0

    # Three-way split of belief: the current season, last season, and — for
    # whatever neither can account for — the positional replacement baseline,
    # applied downstream by shrink_newcomers via `evidence`.
    w_prior = (1.0 - weight) * prior_strength
    own_evidence = weight + w_prior
    for col in RATE_COLUMNS:
        if (merged[f"{col}_prior"].fillna(0) == 0).all():
            # The stat is absent from the prior era entirely (e.g. defensive
            # contribution before 2025/26): an all-zero prior column is a
            # phantom, not evidence — shrinking toward it strangles real
            # current-season signal. Keep current rates unblended.
            continue
        # Renormalised so the value stays "this player's own signal"; the
        # missing mass is spent on the baseline, not silently on zero.
        combined = (weight * merged[col] + w_prior * merged[f"{col}_prior"]) / own_evidence.where(
            own_evidence > 0, 1.0
        )
        merged[col] = combined.where(has_prior, merged[col])
    # Thin evidence is thin whatever its source: a 694-minute prior is not a
    # confident read on a first-choice striker, and the table must say so
    # rather than presenting it with the same face as a 3000-minute season.
    # Anything short of full evidence is flagged. Pre-season an established
    # player scores exactly 1.0 (no current minutes, full-weight prior) so the
    # flag stays off for him; it lights up precisely for the thin-prior players
    # whose confident-looking numbers were the defect — Isak's 8-GW projection
    # rested on 694 injury-wrecked minutes and the table said nothing.
    merged["low_sample"] = own_evidence < FULL_EVIDENCE - 1e-9
    merged["has_prior"] = has_prior
    merged["prior_strength"] = prior_strength
    # evidence = weight this player's OWN numbers have earned (current +
    # graded prior); the shortfall drives the baseline haircut downstream.
    merged["evidence"] = own_evidence
    return merged[
        [
            "id", "minutes_sample", *RATE_COLUMNS,
            "low_sample", "has_prior", "prior_strength", "evidence",
        ]
    ]


def shrink_newcomers(blended: pd.DataFrame, element_type: pd.Series) -> pd.DataFrame:
    """Regress under-evidenced players' rates toward a positional replacement
    baseline by their evidence weight.

    `blend` shrinks a player toward his own prior; whatever weight neither the
    current season nor a graded prior can account for is spent HERE, on a low
    percentile of established players at the same position. Two populations
    need it, for the same reason:

      * genuine newcomers (no prior at all) — otherwise a two-game hot streak
        outranks an established player's blended prior (knowledge.md:
        Ekitiké 71' vs Wood's 20-goal season);
      * players whose prior is THIN — a zeroed row (loan abroad, season-long
        injury) or a fragment of a season. Before this, a zeroed prior was
        weighted 1.0 and read as a measured zero: Rashford carried
        xg90 = xa90 = 0.00 at £7.0m on the 2026-07-25 run.

    The haircut is heaviest with the least evidence and decays to nothing at
    full evidence, so an established player's numbers are untouched — at
    prior_strength 1 and no current minutes this is arithmetically identical
    to the previous behaviour.

    Baselines are defined by FULLY established players only; letting a
    half-evidenced player help set the bar he is then measured against would
    drag the baseline toward the very rows we distrust.

    `element_type` is a Series indexed by player id (FPL element_type 1-4).
    """
    if not {"has_prior", "evidence"}.issubset(blended.columns):
        return blended
    out = blended.copy()
    et = out["id"].map(element_type)
    established = out[out["evidence"] >= FULL_EVIDENCE]
    est_et = established["id"].map(element_type)
    baselines: dict[Any, dict[str, float]] = {}
    for pos, grp in established.groupby(est_et):
        if len(grp) >= MIN_BASELINE_POPULATION:
            baselines[pos] = {
                c: float(grp[c].quantile(NEWCOMER_BASELINE_QUANTILE)) for c in RATE_COLUMNS
            }
    under_evidenced = out["evidence"] < FULL_EVIDENCE
    for col in RATE_COLUMNS:
        base = et.map(lambda p: baselines.get(p, {}).get(col))
        apply = under_evidenced & base.notna()
        if not apply.any():
            continue
        w = out.loc[apply, "evidence"]
        out.loc[apply, col] = w * out.loc[apply, col] + (1 - w) * base[apply]
    return out

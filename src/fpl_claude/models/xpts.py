"""Expected points: the rules-driven scoring map — the layer we BUILD.

This is deliberately a thin, transparent layer: every scoring value comes from
`config/rules/{season}.yaml` via the rules engine, never hard-coded, so when the
2026/27 rules are verified at season launch (chip counts, defensive-contribution
thresholds...) the projections change by editing YAML, not code.

Composition per player per fixture:

  appearance   p60 * gte_60 + (p_play - p60) * lt_60
  goals        exp_min/90 * xg90 * attack_scale * goal_pts[pos]
  assists      exp_min/90 * xa90 * attack_scale * assist_pts
  clean sheet  p60 * cs_prob * cs_pts[pos]           (60' required by rule)
  conceded     -E[floor(K/2)], K ~ Poisson(opp_xg * exp_min/90)   (GKP/DEF)
  saves        exp_min/90 * saves90 / saves_per_n    (GKP)
  def. contrib dc_pts[pos] * P(Poisson(dc90 * exp_min/90) >= threshold)
  bonus        bonus90 * exp_min/90                  (historical proxy, v1)
  penalty      exp_min/90 * team_pen_goals90 * embed_gap * goal_pts[pos]

attack_scale = fixture expected goals / league average — how much easier or
harder this opponent makes scoring than the player's per-90 baseline. Penalties
are fixture-independent (a spot-kick is a spot-kick) so the penalty term is NOT
attack-scaled.

The penalty term prices the designated taker's spot-kicks. FPL's `expected_goals`
already embeds a full-history taker's own penalties, so crediting an established
taker again would double-count — `embed_gap` credits only the share his xg90
cannot have captured yet: a priorless newcomer taker whose rate is shrunk toward
replacement (auto, decaying as his own minutes accumulate), or an explicit news
overlay `pen_boost` for a mid-season duty change among established players
(steady state: has_prior taker, no overlay -> embed_gap 0 -> xg90 unchanged). The
edge this exists to catch is a NEW taker the market/model underrates, exactly the
minutes-adjacent inefficiency the project chases.

Component applicability is ENFORCED by position, never assumed from the data:

  component     GKP  DEF  MID  FWD   enforced by
  appearance     x    x    x    x    —
  goals          -    x    x    x    STRUCTURALLY_ZERO (a keeper isn't scoring;
                                     rates can't be trusted to guarantee that)
  assists        x    x    x    x    rate-driven (keeper assists are real, rare)
  clean sheet    x    x    x    -    YAML clean_sheet points (FWD: 0)
  conceded       x    x    -    -    YAML goals_conceded_per_2 position list
  saves          x    -    -    -    GKP-only branch
  def. contrib   -    x    x    x    YAML defensive_contribution position list
  bonus          x    x    x    x    —
  penalty        -    x    x    x    designated-taker branch (pen_taker); a
                                     keeper's spot-kicks are not modeled

Unknown positions raise rather than silently score as outfielders.

Not modeled in v1 (documented, small, roughly netting out): cards, own goals,
penalty saves/misses. The backtest gate decides if that stays acceptable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..rules.engine import Ruleset
from .minutes import MinutesEstimate
from .team import LEAGUE_AVG_GOALS, FixtureExpectation

MAX_GOALS = 15  # Poisson truncation, matches the team model's score grid

# Expected penalty GOALS per team per 90: PL awards ~0.10 penalties per team per
# game and they convert at ~0.79 -> ~0.08 goals. The designated taker inherits
# this stream; a benched taker takes none, so it is minutes-shared like any other
# component. A constant (not team-specific): pens-won rate is noisy at team level
# and the taker identity, not his club's pen-drawing, is the signal we price.
TEAM_PEN_GOALS_PER90 = 0.08

POSITIONS = frozenset({"GKP", "DEF", "MID", "FWD"})
PENALTY_POSITIONS = frozenset({"DEF", "MID", "FWD"})

# Components forced to zero regardless of what the rates data claims — the
# structural truths of the game the pipeline must not depend on clean data for.
STRUCTURALLY_ZERO: dict[str, frozenset[str]] = {"GKP": frozenset({"goals"})}


def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)


def poisson_sf(k: int, lam: float) -> float:
    """P(K >= k) for K ~ Poisson(lam)."""
    if k <= 0:
        return 1.0
    return max(0.0, 1.0 - sum(poisson_pmf(i, lam) for i in range(k)))


def expected_floor_half(lam: float) -> float:
    """E[floor(K/2)] for K ~ Poisson(lam) — the goals-conceded penalty unit."""
    return sum((k // 2) * poisson_pmf(k, lam) for k in range(MAX_GOALS + 1))


@dataclass(frozen=True)
class ScoringMap:
    appearance_lt60: float
    appearance_gte60: float
    goal_points: dict[str, float]
    assist_points: float
    cs_points: dict[str, float]
    conceded_per_2: dict[str, float]  # negative values, e.g. {"GKP": -1, "DEF": -1}
    saves_per_n: int
    dc_rules: dict[str, dict[str, float]]  # pos -> {points, threshold}

    @classmethod
    def from_ruleset(cls, rules: Ruleset) -> "ScoringMap":
        s = rules.raw["scoring"]
        dc = {
            pos: {"points": v["points"], "threshold": v["threshold"]}
            for pos, v in s.get("defensive_contribution", {}).items()
            if isinstance(v, dict) and "points" in v
        }
        return cls(
            appearance_lt60=s["appearance"]["lt_60_min"],
            appearance_gte60=s["appearance"]["gte_60_min"],
            goal_points={k: float(v) for k, v in s["goals"].items()},
            assist_points=float(s["assists"]),
            cs_points={k: float(v) for k, v in s["clean_sheet"].items()},
            conceded_per_2={k: float(v) for k, v in s["goals_conceded_per_2"].items()},
            saves_per_n=3 if "saves_per_3" in s else int(s.get("saves_per_n", 3)),
            dc_rules=dc,
        )


def expected_points(
    position: str,
    rates: dict[str, Any],
    minutes: MinutesEstimate,
    fixture: FixtureExpectation,
    is_home: bool,
    scoring: ScoringMap,
) -> dict[str, float]:
    """Component-wise expected points for one player in one fixture.

    Returns every component plus 'total' so decision memos can show the
    decomposition — an opaque final number is exactly what we refused to
    extract from third-party sites.
    """
    if position not in POSITIONS:
        raise ValueError(f"unknown position {position!r}; expected one of {sorted(POSITIONS)}")
    team_xg = fixture.home_xg if is_home else fixture.away_xg
    opp_xg = fixture.away_xg if is_home else fixture.home_xg
    cs_prob = fixture.home_cs_prob if is_home else fixture.away_cs_prob

    share = minutes.exp_minutes / 90.0
    attack_scale = team_xg / LEAGUE_AVG_GOALS

    appearance = minutes.p60 * scoring.appearance_gte60 + (
        minutes.p_play - minutes.p60
    ) * scoring.appearance_lt60
    goals = share * rates["xg90"] * attack_scale * scoring.goal_points[position]
    assists = share * rates["xa90"] * attack_scale * scoring.assist_points
    clean_sheet = minutes.p60 * cs_prob * scoring.cs_points.get(position, 0.0)

    conceded = 0.0
    if position in scoring.conceded_per_2:
        conceded = scoring.conceded_per_2[position] * expected_floor_half(opp_xg * share)

    saves = 0.0
    if position == "GKP":
        saves = share * rates["saves90"] / scoring.saves_per_n

    defensive_contribution = 0.0
    dc_rule = scoring.dc_rules.get(position)
    if dc_rule and rates.get("dc90"):
        p_hit = poisson_sf(int(dc_rule["threshold"]), rates["dc90"] * share)
        defensive_contribution = dc_rule["points"] * p_hit

    bonus = rates.get("bonus90", 0.0) * share

    penalty = 0.0
    if position in PENALTY_POSITIONS and rates.get("pen_taker"):
        # Credit only the penalty share the player's xg90 cannot already embed.
        # has_prior taker => his prior xg90 prices his pens (auto_gap 0); a
        # priorless newcomer's rate is shrunk toward replacement and prices none
        # (auto_gap -> 1, decaying to 0 as his own minutes earn full weight). A
        # news overlay (pen_boost) forces the term on for a duty change among
        # established players — the one case stats alone cannot see.
        has_prior = bool(rates.get("has_prior", True))
        evidence = float(rates.get("evidence", 1.0))
        auto_gap = 0.0 if has_prior else max(0.0, 1.0 - evidence)
        embed_gap = max(auto_gap, float(rates.get("pen_boost", 0.0)))
        penalty = share * TEAM_PEN_GOALS_PER90 * embed_gap * scoring.goal_points[position]

    components = {
        "appearance": appearance,
        "goals": goals,
        "assists": assists,
        "clean_sheet": clean_sheet,
        "conceded": conceded,
        "saves": saves,
        "defensive_contribution": defensive_contribution,
        "bonus": bonus,
        "penalty": penalty,
    }
    for name in STRUCTURALLY_ZERO.get(position, ()):
        components[name] = 0.0
    components["total"] = sum(components.values())
    return {k: round(v, 3) for k, v in components.items()}

"""Minutes model v1 — the layer we BUILD, never extract.

Minutes are our edge (CLAUDE.md rule 2): most FPL points are lost to benchings,
and no off-the-shelf projection lets us override its minutes assumptions with our
own team-news intelligence. This v1 is a transparent heuristic on FPL API fields;
the LightGBM upgrade trained on vaastav history (`minutes_v2.py`) replaces
`_start_share` and `_p60_given_start` without changing the interface.

Per player we estimate:
  p_start      P(named in the XI)
  p_cameo      P(appears off the bench)
  p60          P(plays 60+ minutes)  — gates clean-sheet and full appearance pts
  exp_minutes  expected minutes for one fixture

Three inputs the API can't give us are injected explicitly:
  priors   pre-season (or tiny-sample) start shares, e.g. from last season's
           final bootstrap snapshot via `priors_from_bootstrap`
  model    v2 `ModelMinutes` per player (see `minutes_v2.MinutesModelV2`), which
           supersedes the heuristic's start share and minutes shape where it has
           enough history; absent or None, this file behaves exactly as before
  overlay  per-player overrides written by the news-sweep/plan skills, each one
           carrying a written reason (auditable in the decision memo)

The precedence is deliberate and never changes: **overlay > model > heuristic**.
A trained model that has never read a press conference does not get to overrule
a written team-news read (CLAUDE.md rule 4), and availability flags stay an
explicit multiplier on top of all three because no archive we can train on
carries historical injury status.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

# Availability by FPL status flag when chance_of_playing_next_round is null.
DEFAULT_AVAILABILITY = {
    "a": 1.0,   # available
    "d": 0.75,  # doubtful with no % — FPL convention is ~75%
    "i": 0.0,   # injured
    "s": 0.0,   # suspended
    "u": 0.0,   # unavailable (left club, etc.)
    "n": 0.0,   # not in squad
}

FULL_SEASON_GAMES = 38
DEFAULT_START_MINUTES = 78.0
DEFAULT_CAMEO_MINUTES = 18.0
NEUTRAL_START_SHARE = 0.5  # used only when we have neither data nor a prior
CAMEO_SHARE_OF_NON_STARTS = 0.3  # fringe starters see cameos; nailed players don't


@dataclass(frozen=True)
class ModelMinutes:
    """One player's trained-model minutes shape, handed to `estimate`.

    Deliberately expressed as SHARES and CONDITIONALS rather than finished
    probabilities: `estimate` still owns the availability multiplier and the
    overlay precedence, so a model swap can never quietly bypass either. Lives
    here rather than in `minutes_v2` so this module never imports lightgbm — and
    so the v2 file can import it without a cycle.
    """

    start_share: float          # P(starts | available)
    cameo_share: float          # P(bench appearance | available)
    p60_given_start: float      # P(60+ | started)
    minutes_given_start: float  # E[minutes | started]
    cameo_minutes: float = DEFAULT_CAMEO_MINUTES


@dataclass(frozen=True)
class MinutesEstimate:
    player_id: int
    p_start: float
    p_cameo: float
    p60: float
    exp_minutes: float
    confidence: str  # "season" (current data), "prior" (injected), "neutral"
    overlay_reason: str | None = None

    @property
    def p_play(self) -> float:
        return min(1.0, self.p_start + self.p_cameo)


def availability(player: dict[str, Any]) -> float:
    """P(available for selection) from the FPL flag + stated chance."""
    chance = player.get("chance_of_playing_next_round")
    if chance is not None:
        return max(0.0, min(1.0, float(chance) / 100.0))
    return DEFAULT_AVAILABILITY.get(player.get("status", "a"), 1.0)


def _start_share(
    player: dict[str, Any], team_games: int, prior: float | None
) -> tuple[float, str]:
    """Share of team games this player starts, with pre-season fallback."""
    starts = int(player.get("starts") or 0)
    if team_games >= 3:  # enough current-season signal to trust
        return min(1.0, starts / team_games), "season"
    if prior is not None:
        if team_games > 0:  # tiny sample: blend current into the prior
            current = starts / team_games
            weight = team_games / 3.0
            return min(1.0, weight * current + (1 - weight) * prior), "prior"
        return min(1.0, prior), "prior"
    if team_games > 0:  # tiny sample, no prior: shrink toward neutral, don't
        current = starts / team_games  # let 1 start in 1 game read as p_start 1.0
        weight = team_games / 3.0
        return min(1.0, weight * current + (1 - weight) * NEUTRAL_START_SHARE), "season"
    return NEUTRAL_START_SHARE, "neutral"


def _p60_given_start(player: dict[str, Any]) -> float:
    """P(60+ | started): from average minutes per start when we have it."""
    starts = int(player.get("starts") or 0)
    minutes = int(player.get("minutes") or 0)
    if starts > 0:
        return max(0.5, min(0.98, (minutes / starts) / 90.0 + 0.05))
    return 0.85


def estimate(
    player: dict[str, Any],
    team_games: int,
    prior_start_share: float | None = None,
    overlay: dict[str, Any] | None = None,
    model: ModelMinutes | None = None,
) -> MinutesEstimate:
    """Minutes estimate for one player for one fixture.

    overlay: {"start_share": float, "reason": str} — an explicit, written-down
    override from team-news intelligence (rotation pattern, presser quote, leak).
    model:   a v2 `ModelMinutes` for this player, or None for the pure heuristic.
             With model=None the arithmetic below is the original v1 line for
             line, which is what keeps the backtest and the test suite stable.
    """
    avail = availability(player)
    share, confidence = _start_share(player, team_games, prior_start_share)
    p60_given_start = _p60_given_start(player)
    start_minutes = DEFAULT_START_MINUTES
    cameo_minutes = DEFAULT_CAMEO_MINUTES
    cameo_share = max(0.0, 1.0 - share) * CAMEO_SHARE_OF_NON_STARTS

    if model is not None:
        share = max(0.0, min(1.0, float(model.start_share)))
        cameo_share = max(0.0, min(1.0 - share, float(model.cameo_share)))
        p60_given_start = max(0.0, min(1.0, float(model.p60_given_start)))
        start_minutes = max(0.0, min(90.0, float(model.minutes_given_start)))
        cameo_minutes = max(0.0, min(90.0, float(model.cameo_minutes)))
        confidence = "model"

    reason = None
    if overlay is not None:
        # The overlay speaks to whether he STARTS; how long he lasts once he
        # does is still the model's (or the heuristic's) business.
        share = max(0.0, min(1.0, float(overlay["start_share"])))
        cameo_share = max(0.0, 1.0 - share) * CAMEO_SHARE_OF_NON_STARTS
        reason = str(overlay.get("reason", "")) or None
        confidence = "overlay"

    p_start = avail * share
    p_cameo = avail * cameo_share
    p60 = p_start * p60_given_start
    exp_minutes = p_start * start_minutes + p_cameo * cameo_minutes
    return MinutesEstimate(
        player_id=int(player["id"]),
        p_start=round(p_start, 4),
        p_cameo=round(p_cameo, 4),
        p60=round(p60, 4),
        exp_minutes=round(exp_minutes, 2),
        confidence=confidence,
        overlay_reason=reason,
    )


def estimate_all(
    bootstrap: dict[str, Any],
    team_games: dict[int, int],
    priors: dict[int, float] | None = None,
    overlays: dict[int, dict[str, Any]] | None = None,
    model: Mapping[int, ModelMinutes] | None = None,
) -> pd.DataFrame:
    """Estimates for every player. team_games: team_id -> PL games played.

    model: player id -> `ModelMinutes`, typically
    `minutes_v2.MinutesModelV2.predict_gw(...)`. Players missing from the mapping
    (cold starts, new signings) fall through to the heuristic's prior path, which
    is the honest answer for a player nobody has minutes data on yet.
    """
    priors = priors or {}
    overlays = overlays or {}
    model = model or {}
    rows = []
    for p in bootstrap["elements"]:
        est = estimate(
            p,
            team_games.get(p["team"], 0),
            priors.get(p["id"]),
            overlays.get(p["id"]),
            model.get(p["id"]),
        )
        rows.append(
            {
                "id": est.player_id,
                "p_start": est.p_start,
                "p_cameo": est.p_cameo,
                "p_play": est.p_play,
                "p60": est.p60,
                "exp_minutes": est.exp_minutes,
                "minutes_confidence": est.confidence,
                "overlay_reason": est.overlay_reason,
            }
        )
    return pd.DataFrame(rows)


def priors_from_bootstrap(prior_bootstrap: dict[str, Any]) -> dict[int, float]:
    """Start-share priors from a previous season's final bootstrap snapshot.

    Keyed by FPL player id — ids persist across seasons for continuing players;
    new signings simply have no prior and fall back to neutral (a real unknown
    the overlay must resolve from news, which is honest).
    """
    priors: dict[int, float] = {}
    for p in prior_bootstrap["elements"]:
        starts = int(p.get("starts") or 0)
        if starts:
            priors[int(p["id"])] = min(1.0, starts / FULL_SEASON_GAMES)
    return priors


def team_games_played(fixtures: list[dict[str, Any]]) -> dict[int, int]:
    """PL games finished per team, from the fixtures list."""
    games: dict[int, int] = {}
    for fx in fixtures:
        if fx.get("finished"):
            for side in ("team_h", "team_a"):
                games[fx[side]] = games.get(fx[side], 0) + 1
    return games

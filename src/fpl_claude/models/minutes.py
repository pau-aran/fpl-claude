"""Minutes model v1 — the layer we BUILD, never extract.

Minutes are our edge (CLAUDE.md rule 2): most FPL points are lost to benchings,
and no off-the-shelf projection lets us override its minutes assumptions with our
own team-news intelligence. This v1 is a transparent heuristic on FPL API fields;
the LightGBM upgrade trained on vaastav history replaces `_start_share` and
`_p60_given_start` in Phase 2b without changing the interface.

Per player we estimate:
  p_start      P(named in the XI)
  p_cameo      P(appears off the bench)
  p60          P(plays 60+ minutes)  — gates clean-sheet and full appearance pts
  exp_minutes  expected minutes for one fixture

Two inputs the API can't give us are injected explicitly:
  priors   pre-season (or tiny-sample) start shares, e.g. from last season's
           final bootstrap snapshot via `priors_from_bootstrap`
  overlay  per-player overrides written by the news-sweep/plan skills, each one
           carrying a written reason (auditable in the decision memo)
"""

from __future__ import annotations

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

# Prior minutes at which last season's start share is trusted in full. Below
# it the prior is partial evidence and is regressed toward neutral: 694 minutes
# around a fibula fracture is not a read on a first-choice striker, and the old
# code priced Isak at 5.35 xPts over 8 GWs because it treated it as one.
# 900' = ten full matches.
PRIOR_FULL_WEIGHT_MINUTES = 900

# How much of a prior start share survives a summer club change. Last season's
# minutes are evidence about the PLAYER but not about his place in a new team's
# pecking order — Dubravka's 35 Newcastle starts made him the highest xPts/£m
# player in the game as a 37-year-old third-choice Spurs keeper. Kept well
# above zero because a nailed starter usually does not move to sit on a bench.
CLUB_CHANGE_PRIOR_RETENTION = 0.5


@dataclass(frozen=True)
class StartSharePrior:
    """Last season's start share, with the evidence behind it.

    `minutes` grades how much sample the share rests on; `team_code` is the
    club it was earned at (stable across seasons) so a move can be detected.
    """

    share: float
    minutes: int = 0
    team_code: int | None = None


@dataclass(frozen=True)
class MinutesEstimate:
    player_id: int
    p_start: float
    p_cameo: float
    p60: float
    exp_minutes: float
    # "season" (current data), "prior" (full-weight last season), "prior_thin"
    # (last season, but few minutes behind it), "prior_new_club" (last season,
    # different club), "neutral" (no evidence), "overlay" (manager override)
    confidence: str
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


def _discount_prior(
    prior: StartSharePrior, current_team_code: int | None
) -> tuple[float, str]:
    """Regress a prior start share toward neutral by how much it is worth here.

    Two independent discounts, because "37 starts last season" can mean very
    different things:

      * THIN — few minutes behind the share. The share cannot tell a player
        who was benched from one who was injured, so a fragment of a season is
        regressed toward neutral rather than believed.
      * NEW CLUB — the share was earned in a different team's pecking order.
        Evidence about the player, not about his place in this squad.

    Both are applied, so a thin prior at a new club is discounted twice.
    """
    strength = min(1.0, prior.minutes / PRIOR_FULL_WEIGHT_MINUTES) if prior.minutes else 1.0
    label = "prior" if strength >= 1.0 else "prior_thin"
    if (
        prior.team_code is not None
        and current_team_code is not None
        and int(prior.team_code) != int(current_team_code)
    ):
        strength *= CLUB_CHANGE_PRIOR_RETENTION
        label = "prior_new_club"
    share = strength * prior.share + (1 - strength) * NEUTRAL_START_SHARE
    return min(1.0, share), label


def _start_share(
    player: dict[str, Any],
    team_games: int,
    prior: StartSharePrior | None,
    current_team_code: int | None = None,
) -> tuple[float, str]:
    """Share of team games this player starts, with pre-season fallback."""
    starts = int(player.get("starts") or 0)
    if team_games >= 3:  # enough current-season signal to trust
        return min(1.0, starts / team_games), "season"
    if prior is not None:
        prior_share, label = _discount_prior(prior, current_team_code)
        if team_games > 0:  # tiny sample: blend current into the prior
            current = starts / team_games
            weight = team_games / 3.0
            return min(1.0, weight * current + (1 - weight) * prior_share), label
        return prior_share, label
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
    prior_start_share: StartSharePrior | float | None = None,
    overlay: dict[str, Any] | None = None,
    current_team_code: int | None = None,
) -> MinutesEstimate:
    """Minutes estimate for one player for one fixture.

    overlay: {"start_share": float, "reason": str} — an explicit, written-down
    override from team-news intelligence (rotation pattern, presser quote, leak).

    prior_start_share accepts a bare float for callers that only have a share
    (older snapshots, hand-built tests); it is then trusted at full weight, as
    before. A `StartSharePrior` additionally carries the minutes and club
    behind that share and is discounted accordingly.
    """
    avail = availability(player)
    if isinstance(prior_start_share, (int, float)):
        prior_start_share = StartSharePrior(share=float(prior_start_share))
    share, confidence = _start_share(
        player, team_games, prior_start_share, current_team_code
    )
    reason = None
    if overlay is not None:
        share = max(0.0, min(1.0, float(overlay["start_share"])))
        reason = str(overlay.get("reason", "")) or None
        confidence = "overlay"

    # Bench appearances: fringe starters see cameos; nailed players rarely do.
    cameo_share = max(0.0, (1.0 - share)) * 0.3

    p_start = avail * share
    p_cameo = avail * cameo_share
    p60 = p_start * _p60_given_start(player)
    exp_minutes = p_start * DEFAULT_START_MINUTES + p_cameo * DEFAULT_CAMEO_MINUTES
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
    priors: dict[int, StartSharePrior] | None = None,
    overlays: dict[int, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Estimates for every player. team_games: team_id -> PL games played."""
    priors = priors or {}
    overlays = overlays or {}
    # team id -> stable cross-season club code, so a prior earned elsewhere
    # can be spotted (team ids are reassigned between seasons; codes are not).
    team_codes = {int(t["id"]): t.get("code") for t in bootstrap.get("teams", [])}
    rows = []
    for p in bootstrap["elements"]:
        est = estimate(
            p,
            team_games.get(p["team"], 0),
            priors.get(p["id"]),
            overlays.get(p["id"]),
            current_team_code=team_codes.get(int(p["team"])),
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


def priors_from_bootstrap(prior_bootstrap: dict[str, Any]) -> dict[int, StartSharePrior]:
    """Start-share priors from a previous season's final bootstrap snapshot.

    Keyed by CURRENT-season player id (use `data.season_bridge` to remap a raw
    archive — FPL reassigns ids every season). Players with no prior row simply
    have no entry and fall back to neutral, a real unknown the overlay must
    resolve from news, which is honest.

    Each prior carries the minutes behind it and the club they were played for,
    so `_start_share` can discount evidence that is thin or was earned
    somewhere else — see `StartSharePrior`.
    """
    priors: dict[int, StartSharePrior] = {}
    for p in prior_bootstrap["elements"]:
        starts = int(p.get("starts") or 0)
        if starts:
            priors[int(p["id"])] = StartSharePrior(
                share=min(1.0, starts / FULL_SEASON_GAMES),
                minutes=int(p.get("minutes") or 0),
                team_code=p.get("team_code"),
            )
    return priors


def team_games_played(fixtures: list[dict[str, Any]]) -> dict[int, int]:
    """PL games finished per team, from the fixtures list."""
    games: dict[int, int] = {}
    for fx in fixtures:
        if fx.get("finished"):
            for side in ("team_h", "team_a"):
                games[fx[side]] = games.get(fx[side], 0) + 1
    return games

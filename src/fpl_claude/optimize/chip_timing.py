"""Chip-TIMING advisory surface — when (not whether) to play a chip.

Phase 3b split the chip problem in two. The backtest simulator owns the
MECHANICS (simulate.py: `score_gw`/`run_gameweek`/`wildcard_squad` actually play
wildcard/free_hit/bench_boost/triple_captain and track a one-per-half inventory).
This module owns the TIMING: given the squad we HOLD and the fixtures/projections
ahead, it says which chip is worth playing, in which gameweek, and — just as
often — why NOT to. Chips are ADVICE for the manager; nothing here plays one
(models propose, the manager disposes — CLAUDE.md rule 4).

The rule encoded here is the one the AFCON counterfactual proved
(`reports/backtest/2025-26/chip-analysis-afcon.md`, distilled in knowledge.md):

    TC on a standout captain fixture / DGW;
    BB only on a DGW (all 15 nailed starters with fixtures);
    WC/FH only for a 4+ change need or a BGW/DGW.

...plus the proven NEGATIVE: don't burn a reshaping chip (WC/FH) on an
FT-rideable disruption (a WC held through GW17-20 scored 236 vs 238 on free
transfers — the window's value was reactivity, not a one-shot reshape). The
default posture is therefore CONSERVATIVE: HOLD unless a real trigger fires, and
single-GW chip punts (hoping for bench variance) are treated as noise — the value
is in genuine doubles and blanks, which is why DGW/BGW detection is the spine of
the module.

Everything is pure and I/O-free: fixtures in, projections in, structured advice
out. The caller (backtest run.py --propose, or the live pipeline once live
projections exist) does the I/O and prints the tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .milp import _pick_lineup

# ---------------------------------------------------------------- thresholds
# All gates are explicit module constants so a review can argue with the number,
# not reverse-engineer it from code. The posture is deliberately CONSERVATIVE:
# the counterfactual showed chips HELD beat chips BURNED across a normal window.

DGW_MIN_FIXTURES = 2  # a team playing >= 2 matches in a GW is a DOUBLE
BGW_MAX_FIXTURES = 0  # a team playing 0 matches in a scheduled GW is a BLANK

# 2025/26: chip set 1 = GW1-19, set 2 = GW20-38 (one of each chip per half).
# Owned here (the timing layer) so both this module and the simulator read one
# definition; simulate.py imports it back for its inventory guard.
HALF_BOUNDARY_GW = 19

# TC: the "+1x" beyond the normal captain double equals the captain's single-GW
# xpts. A premium captain projects ~7-9 on a normal fixture; >= 8.0 marks a
# genuine ceiling week (soft/home vs a weak defence) and a DGW captain (whose
# xpts_gw SUMS both fixtures) clears it comfortably. Below the floor, hold TC for
# a bigger fixture — GW17-Haaland (~8.85 single-GW) was the archetype we want to
# catch, a pedestrian ~7 premium week the one we want to skip. The calibration
# [OPEN] note (model UNDER-states premium ceilings in strong weeks) makes 8.0 a
# conservative floor, not an aggressive one.
TC_STANDOUT_XPTS = 8.0

# BB pays only if all four bench slots actually START and hold a fixture, so it
# is gated three ways: a real squad DGW (below), every bench slot NAILED, and the
# four bench players' summed xpts clearing a floor. ~12.0 is four nailed starters
# averaging ~3 xpts — a single-GW bench rarely reaches it (which is the point:
# "BB only on a DGW", where the bench doubles). The AFCON BB gains (+11/+12/+19/
# +5) were bench VARIANCE, not a pre-hoc signal (a known-out Rice sat on the GW19
# bench), so a minutes-nailed, fixture-backed bench is mandatory, not optional.
BB_MIN_EXTRA_EV = 12.0

# A bench player counts as NAILED only if expected to play a full-ish match. 60
# is the appearance-2pt / clean-sheet-eligible mark; below it is cameo/rotation
# risk that wastes a BB slot. (The projections carry one steady-state minutes
# estimate, `exp_minutes_gw`; no per-future-GW minutes column exists, so this is
# the honest best-available nailedness proxy — documented, not hidden.)
NAILED_MIN_MINUTES = 60.0

# "A DGW worth a chip conversation" for THIS squad: at least this many of the 15
# play twice. A one- or two-team micro-double (a single rescheduled fixture) is
# NOT a bench-boost/wildcard trigger; a classic FPL DGW doubles a big chunk of
# the squad. 6/15 = ~40% of the outfield — enough that the chip captures real
# extra fixtures rather than one lucky doubler.
SQUAD_DGW_MIN_DOUBLERS = 6

# WC/FH reshape trigger: the reshape need BEYOND the banked free transfers (the
# uncapped optimizer's change count minus current FTs — the caller nets it). >= this
# many changes the FT budget CANNOT ride means the squad is structurally stale (a
# fixture-swing or returnee window), not an FT-rideable blip. The AFCON WC was wrong
# precisely because its 2-change need sat "far inside the FT budget".
WC_CHANGE_THRESHOLD = 4

_CHIP_ORDER = ("triple_captain", "bench_boost", "wildcard", "free_hit")


def chip_half(gw: int, boundary: int = HALF_BOUNDARY_GW) -> int:
    """Which half-season a GW belongs to (1 = GW1..boundary, 2 = after). Chip
    inventory is one-of-each per half, so this decides whether a used chip is
    spent for the GW we are advising."""
    return 1 if gw <= boundary else 2


# ------------------------------------------------------------------ DGW / BGW


@dataclass(frozen=True)
class GwDoubleBlank:
    """Doubles and blanks for one gameweek. `dgw_teams`/`bgw_teams` hold team
    identifiers — names when an id->name map was supplied to detect_double_blank,
    otherwise the raw fixture team keys."""

    gw: int
    dgw_teams: frozenset[Any]
    bgw_teams: frozenset[Any]


# How many gameweeks ahead a DGW/BGW may be trusted WITHOUT point-in-time
# confirmation. See `knowable_double_blank` for why this gate has to exist at all.
SCHEDULE_KNOWABLE_GWS = 3


def knowable_double_blank(
    double_blank: Mapping[int, GwDoubleBlank],
    current_gw: int,
    known_from: Mapping[int, int] | None = None,
    horizon: int = SCHEDULE_KNOWABLE_GWS,
) -> tuple[dict[int, GwDoubleBlank], list[int]]:
    """Drop doubles/blanks a manager could NOT have known about at `current_gw`.

    THE LEAK THIS CLOSES. A replay reads fixtures from an END-OF-SEASON archive,
    and `SeasonStore.fixtures_at` returns that same final table for every
    gameweek — only the `finished` flag is point-in-time. But most doubles and
    blanks do not exist when the season is published: they are *created* during
    it, when a cup run or a postponement forces a fixture to be rearranged. So
    the chip advisor could see every one of them from GW1, and would happily
    tell a GW26 manager to save the triple captain for a GW33 double that came
    from a rearrangement not yet made. That is hindsight steering the single
    highest-leverage decision a chip season has.

    The gate: a DGW/BGW at gameweek `g` is usable only if
      * `known_from[g] <= current_gw` — research established a date it was public; or
      * `g - current_gw <= horizon` — near enough that the fixture is already
        scheduled and televised, so it needs no separate confirmation.

    Returns the filtered map plus the sorted gameweeks that were SUPPRESSED, so
    callers can print them as unverified rather than hide them. Showing a
    manager "GW33 may double, unconfirmed at this deadline" is honest; letting
    it silently pick the chip week is not.
    """
    known_from = known_from or {}
    kept: dict[int, GwDoubleBlank] = {}
    suppressed: list[int] = []
    for gw, db in double_blank.items():
        if not db.dgw_teams and not db.bgw_teams:
            kept[gw] = db  # nothing anomalous to leak
            continue
        confirmed_at = known_from.get(gw)
        if (confirmed_at is not None and confirmed_at <= current_gw) or (
            gw - current_gw <= horizon
        ):
            kept[gw] = db
        else:
            suppressed.append(gw)
    return kept, sorted(suppressed)


def detect_double_blank(
    fixtures: Sequence[Mapping[str, Any]],
    id_to_name: Mapping[int, str] | None = None,
) -> dict[int, GwDoubleBlank]:
    """Flag DGW and BGW teams per gameweek from a fixtures table.

    Counts fixtures-per-team-per-GW (each fixture contributes to its home and
    away team). A team with >= DGW_MIN_FIXTURES matches in a GW is a DOUBLE; a
    team in the league universe with BGW_MAX_FIXTURES (0) matches in a *scheduled*
    GW (one that has >= 1 fixture) is a BLANK. This is the real WC/FH/BB trigger —
    single-GW chip punts were proven noise; the value lives in doubles and blanks.

    The universe of teams is inferred from every team that appears anywhere in
    the table (the 20 PL clubs), so a future blank shows up as "in the league,
    zero fixtures this GW". Pass `id_to_name` to get team NAMES back (matching the
    projections' `team` column); omit it to keep the raw fixture team keys.
    """
    def label(team: Any) -> Any:
        return id_to_name.get(int(team), team) if id_to_name is not None else team

    universe: set[Any] = set()
    counts: dict[int, dict[Any, int]] = {}
    for fx in fixtures:
        event = fx.get("event")
        if event is None or (isinstance(event, float) and pd.isna(event)):
            continue
        gw = int(event)
        for side in ("team_h", "team_a"):
            team = label(fx[side])
            universe.add(team)
            counts.setdefault(gw, {})[team] = counts.setdefault(gw, {}).get(team, 0) + 1

    out: dict[int, GwDoubleBlank] = {}
    for gw, per_team in counts.items():
        dgw = {t for t, n in per_team.items() if n >= DGW_MIN_FIXTURES}
        bgw = {t for t in universe if per_team.get(t, 0) == BGW_MAX_FIXTURES}
        out[gw] = GwDoubleBlank(gw=gw, dgw_teams=frozenset(dgw), bgw_teams=frozenset(bgw))
    return out


# ------------------------------------------------------------------ EV surface


@dataclass(frozen=True)
class GwChipSurface:
    """Chip-EV snapshot for ONE future gameweek, computed over the squad AS HELD
    (we do not re-optimise the 15 for that GW — the XI/bench split is just the
    best legal lineup on that GW's xpts column, a documented approximation).

    tc_extra:      the best captain candidate's single-GW xpts = the +1x TC adds
                   beyond the normal double. On a DGW the xpts_gw column already
                   SUMS both fixtures, so tc_extra reflects the double for free.
    bb_extra:      sum of the four non-XI (bench) players' xpts that GW.
    bb_nonnailed:  bench slots failing the nailed test (exp_minutes below the
                   floor, or the player's club blanks) — any > 0 kills BB.
    n_doublers/n_blankers: squad players whose club doubles / blanks this GW.
    """

    gw: int
    tc_extra: float
    tc_captain: int
    tc_captain_name: str
    tc_captain_dgw: bool
    bb_extra: float
    bb_bench: tuple[int, ...]
    bb_nonnailed: int
    n_doublers: int
    n_blankers: int

    @property
    def bb_nailed(self) -> bool:
        return self.bb_nonnailed == 0

    @property
    def is_squad_dgw(self) -> bool:
        return self.n_doublers >= SQUAD_DGW_MIN_DOUBLERS

    @property
    def is_squad_bgw(self) -> bool:
        return self.n_blankers > 0


def _gw_columns(columns: Iterable[str]) -> list[tuple[int, str]]:
    """(gw, column) for every `xpts_gw{n}` column, in gameweek order."""
    out = []
    for c in columns:
        c = str(c)
        if c.startswith("xpts_gw") and c[len("xpts_gw"):].isdigit():
            out.append((int(c[len("xpts_gw"):]), c))
    return sorted(out)


def chip_surface(
    projections: pd.DataFrame,
    held_ids: Iterable[int],
    lineup: Mapping[str, Any],
    double_blank: Mapping[int, GwDoubleBlank] | None = None,
) -> list[GwChipSurface]:
    """Per-future-GW chip-EV surface for the squad we HOLD.

    For every `xpts_gw{n}` column in `projections`, split the held 15 into the
    best legal XI + 4-man bench on that GW's score (reusing the optimizer's
    single-GW lineup logic), then read off the TC extra (captain's xpts), the BB
    extra (bench sum), bench nailedness (from `exp_minutes_gw`, plus any blank),
    and — when a `double_blank` map is supplied — how many of the 15 double or
    blank. `held_ids` are the owned players (in the backtest, state.buy_costs).
    """
    held = list(dict.fromkeys(int(i) for i in held_ids))
    by_id = projections.drop_duplicates("id").set_index("id")
    pos = {i: by_id.loc[i, "position"] for i in held}
    team = {i: by_id.loc[i, "team"] for i in held}
    exp_minutes = {
        i: float(by_id.loc[i].get("exp_minutes_gw", 0.0) or 0.0) for i in held
    }

    surface: list[GwChipSurface] = []
    for gw, col in _gw_columns(by_id.columns):
        score = {i: float(by_id.loc[i, col]) for i in held}
        _xi, captain, _vice, bench = _pick_lineup(held, score, pos, lineup)

        db = double_blank.get(gw) if double_blank else None
        dgw_teams = db.dgw_teams if db else frozenset()
        bgw_teams = db.bgw_teams if db else frozenset()

        nonnailed = sum(
            1
            for i in bench
            if exp_minutes[i] < NAILED_MIN_MINUTES or team[i] in bgw_teams
        )
        surface.append(
            GwChipSurface(
                gw=gw,
                tc_extra=round(score[captain], 2),
                tc_captain=captain,
                tc_captain_name=str(by_id.loc[captain, "web_name"]),
                tc_captain_dgw=team[captain] in dgw_teams,
                bb_extra=round(sum(score[i] for i in bench), 2),
                bb_bench=tuple(bench),
                bb_nonnailed=nonnailed,
                n_doublers=sum(1 for i in held if team[i] in dgw_teams),
                n_blankers=sum(1 for i in held if team[i] in bgw_teams),
            )
        )
    return surface


# --------------------------------------------------------------------- advice


@dataclass(frozen=True)
class ChipAdvice:
    """One chip's verdict. `verdict` is "advise" or "hold"; `target_gw` is the GW
    to play it when advised; `extra_ev` is the marginal EV number that carried the
    call (TC/BB — None for the reshape chips); `reason` is a one-line rationale
    that also states the NEGATIVE form when holding."""

    chip: str
    verdict: str
    target_gw: int | None
    extra_ev: float | None
    reason: str


def _used_this_half(chip: str, chips_used: Sequence[str], half: int, boundary: int) -> int | None:
    """The GW at which `chip` was spent in this half, or None if still available."""
    for entry in chips_used:
        name, _, gw = str(entry).partition("@")
        if name == chip and gw.isdigit() and chip_half(int(gw), boundary) == half:
            return int(gw)
    return None


def _advise_tc(candidates: list[GwChipSurface]) -> tuple[str, int | None, float | None, str]:
    if not candidates:
        return "hold", None, None, "TC hold: no scored GW in this half's horizon"
    best = max(candidates, key=lambda s: s.tc_extra)
    if best.tc_extra >= TC_STANDOUT_XPTS or best.tc_captain_dgw:
        trigger = "DGW" if best.tc_captain_dgw else "standout fixture"
        return (
            "advise", best.gw, best.tc_extra,
            f"TC advise GW{best.gw}: {best.tc_captain_name} {best.tc_extra} single-GW xpts ({trigger})",
        )
    return (
        "hold", None, best.tc_extra,
        f"TC hold: peak captain {best.tc_extra} xpts < {TC_STANDOUT_XPTS} floor, no DGW in horizon",
    )


def _advise_bb(candidates: list[GwChipSurface]) -> tuple[str, int | None, float | None, str]:
    dgw = [s for s in candidates if s.is_squad_dgw and not s.is_squad_bgw]
    if not dgw:
        # No squad DGW: the primary gate fails. Colour the reason with the
        # best-EV bench's nailedness so the negative form is specific.
        best = max(candidates, key=lambda s: s.bb_extra) if candidates else None
        parts = []
        if best and best.bb_nonnailed:
            parts.append(f"{best.bb_nonnailed} bench slots non-nailed")
        parts.append("no DGW in horizon")
        ev = best.bb_extra if best else None
        return "hold", None, ev, "BB not advised: " + "; ".join(parts)
    target = max(dgw, key=lambda s: s.bb_extra)
    if target.bb_nonnailed:
        return (
            "hold", None, target.bb_extra,
            f"BB not advised: {target.bb_nonnailed} bench slots non-nailed (need 4 nailed starters)",
        )
    if target.bb_extra < BB_MIN_EXTRA_EV:
        return (
            "hold", None, target.bb_extra,
            f"BB hold: bench EV {target.bb_extra} < {BB_MIN_EXTRA_EV} floor on the DGW",
        )
    return (
        "advise", target.gw, target.bb_extra,
        f"BB advise GW{target.gw}: DGW ({target.n_doublers}/15 double), 4 nailed bench, +{target.bb_extra} EV",
    )


def _reshape_events(candidates: list[GwChipSurface]) -> tuple[GwChipSurface | None, GwChipSurface | None]:
    """Earliest squad-BGW and squad-DGW in the candidate window (or None)."""
    bgw = next((s for s in candidates if s.is_squad_bgw), None)
    dgw = next((s for s in candidates if s.is_squad_dgw), None)
    return bgw, dgw


def _advise_wc(
    candidates: list[GwChipSurface], change_need: int | None
) -> tuple[str, int | None, float | None, str]:
    bgw, dgw = _reshape_events(candidates)
    if change_need is not None and change_need >= WC_CHANGE_THRESHOLD:
        return "advise", None, None, f"WC advise: {change_need}+ change need (structural reshape)"
    if bgw is not None:
        return "advise", bgw.gw, None, f"WC advise GW{bgw.gw}: BGW ({bgw.n_blankers}/15 blank)"
    if dgw is not None:
        return "advise", dgw.gw, None, f"WC advise GW{dgw.gw}: DGW ({dgw.n_doublers}/15 double)"
    need = "unknown" if change_need is None else str(change_need)
    return "hold", None, None, f"WC hold: no 4+ change need (need {need}), no BGW/DGW in horizon"


def _advise_fh(candidates: list[GwChipSurface]) -> tuple[str, int | None, float | None, str]:
    bgw, dgw = _reshape_events(candidates)
    if bgw is not None:
        return "advise", bgw.gw, None, f"FH advise GW{bgw.gw}: BGW ({bgw.n_blankers}/15 blank), field a full XI"
    if dgw is not None:
        return "advise", dgw.gw, None, f"FH advise GW{dgw.gw}: DGW ({dgw.n_doublers}/15 double)"
    return "hold", None, None, "FH hold: no BGW/DGW in horizon (a permanent reshape need is a wildcard)"


def advise(
    surface: Sequence[GwChipSurface],
    chips_used: Sequence[str],
    current_gw: int,
    change_need: int | None = None,
    half_boundary_gw: int = HALF_BOUNDARY_GW,
    exclude_gws: Sequence[int] = (),
) -> dict[str, ChipAdvice]:
    """Apply the timing rule to a chip-EV surface → one verdict per chip.

    Only the CURRENT half's chips are in play: candidate GWs are the surface GWs
    in the same half as `current_gw`, and a chip already spent this half returns a
    HOLD ("already used") regardless of EV (the inventory guard the simulator
    enforces mechanically). Everything else follows the knowledge.md rule — TC on
    a standout/DGW captain, BB only on a nailed DGW, WC/FH only on a 4+ change need
    (`change_need`, the reshape magnitude the free-transfer budget CANNOT cover) or
    a BGW/DGW. Default posture is HOLD; the reasons carry the negative form.

    `exclude_gws` drops gameweeks outright — pass the gameweeks
    `knowable_double_blank` suppressed. Stripping the DGW *flag* is not enough
    on its own: a doubling team's `xpts_gw{n}` column already SUMS both of its
    fixtures, so an unknowable double still shows up as a huge single-GW score
    and the TC verdict re-derives it as a "standout fixture". The gameweek has
    to leave the candidate set, not just lose its label.
    """
    half = chip_half(current_gw, half_boundary_gw)
    excluded = set(exclude_gws)
    candidates = [
        s for s in surface
        if chip_half(s.gw, half_boundary_gw) == half and s.gw not in excluded
    ]

    builders = {
        "triple_captain": lambda: _advise_tc(candidates),
        "bench_boost": lambda: _advise_bb(candidates),
        "wildcard": lambda: _advise_wc(candidates, change_need),
        "free_hit": lambda: _advise_fh(candidates),
    }
    out: dict[str, ChipAdvice] = {}
    for chip in _CHIP_ORDER:
        used_gw = _used_this_half(chip, chips_used, half, half_boundary_gw)
        if used_gw is not None:
            out[chip] = ChipAdvice(
                chip=chip, verdict="hold", target_gw=None, extra_ev=None,
                reason=f"{chip} hold: already used in half {half} (at GW{used_gw})",
            )
            continue
        verdict, target, ev, reason = builders[chip]()
        out[chip] = ChipAdvice(
            chip=chip, verdict=verdict, target_gw=target, extra_ev=ev, reason=reason
        )
    return out

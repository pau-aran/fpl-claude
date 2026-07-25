"""Automatic predicted-vs-actual calibration log for `/fpl-review`.

Closes backlog item A3. Until now the calibration step of the review was a
HAND-WRITTEN note ("once models are live, log predicted-vs-actual per position");
the only real decomposition we had was the post-hoc backtest study in
`notebooks/calibration_analysis.py` / `reports/backtest/2025-26/calibration.md`.
This module makes the loop automatic: it takes the PREDICTED side from a
`db/projections/{YYYY-MM-DD}.csv` snapshot, the ACTUAL side from either the live
FPL API or a committed backtest `gw{NN}_players.csv`, joins them on the FPL
player id (the canonical key everywhere in this repo) and appends one section per
gameweek to an append-only markdown log.

Error convention throughout — identical to `calibration_analysis.py` and the A2
report so the two are directly comparable:

    error = actual - predicted      (POSITIVE = the week OUT-scored the model)

What it reproduces and extends from the closed 20-GW decomposition (A2):

  * The residual is NOT captain-only. The small mean under-prediction (+4.3/GW
    over 2025/26) lives in the BASE XI and sits inside sampling noise (t = 1.47,
    ns), while the DOUBLED captain slot is mean-UNBIASED (-0.07) and merely
    high-variance. So base XI and captain slot are logged SEPARATELY, using the
    same split the memo Outcome line prints (`backtest.simulate.XiBreakdown`:
    base XI = counted players EXCLUDING the captain; captain slot = captain xPts
    x his multiplier). The alternative cut used for the headline table in
    `calibration.md` (XI with the captain counted ONCE, plus the doubled EXTRA
    copy) is logged alongside it, so both framings reconcile to one total.
  * `ep_next` — FPL's own next-GW prediction, carried through the projections
    CSV — is logged side by side as an independent benchmark. It is genuinely
    absent (NaN) in the backtest archive, so every statistic over it is
    NaN-dropping and reports its own `n`. Where FPL's number beat ours the log
    names the players, because the review's job is to ask WHAT IT SAW (usually
    minutes, or a set-piece/penalty role) and feed that back.
  * OWNED players (the squad — what actually cost us points) are reported
    separately from the WHOLE POOL (model quality at large). The review cares
    about both, differently: the pool measures the model, the squad measures the
    season.

**Point-in-time honesty is the load-bearing property.** The predicted CSV for
GW n must be one written BEFORE that gameweek's deadline, or the log is worse
than useless — it would launder hindsight into a "calibration". Selection is
therefore deliberate and auditable (`select_snapshot`): candidates are the
`YYYY-MM-DD.csv` files in the projections dir, anything dated after the deadline
day is REJECTED (and warned about, never silently skipped), a file dated ON the
deadline day must also have an mtime at or before the deadline, and the chosen
file's name is recorded in the log itself. If nothing qualifies the run REFUSES
(`PointInTimeError`) rather than reaching for a post-deadline file.

Wedges NOT modelled here (declared, not hidden): auto-subs and points hits. Both
are squad-accounting wedges owned by the backtest runner's memo maths, not
prediction error; `calibration.md` measured them at +1.15/GW and -4 all season
respectively. The slot table below is therefore pre-autosub, pre-hit — the same
basis the projections were made on.

CLI:
    python -m fpl_claude.reports.calibration --gw 12
    python -m fpl_claude.reports.calibration --gw 12 --from-snapshot 2026-11-28
    python -m fpl_claude.reports.calibration --gw 12 --actuals backtest \\
        --backtest-players reports/backtest/2025-26/gw12_players.csv \\
        --snapshot db/projections/2026-11-28.csv --deadline 2026-11-28T18:30:00Z
"""

from __future__ import annotations

import argparse
import json
import math
import statistics as st
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..data.fpl_api import PROJECT_ROOT, RAW_DIR, get_bootstrap, get_event_live

# ------------------------------------------------------------------ constants

PROJECTIONS_DIR = PROJECT_ROOT / "db" / "projections"

# The log lives next to the reproducible backtest analysis it extends, and is
# exactly the path `/fpl-review` step 5 already pointed at. `reports/` holds
# rendered deliverables and `db/` is gitignored data; this file is neither — it
# is the model's own audit trail, committed, append-only, beside the notebook
# that established its conventions.
DEFAULT_LOG = PROJECT_ROOT / "notebooks" / "calibration.md"

POSITIONS = ("GKP", "DEF", "MID", "FWD")
XI_ROLES = ("C", "V", "XI")  # role codes in gw{NN}_players.csv that field a player
CAPTAIN_ROLE = "C"
VICE_ROLE = "V"

# A player who reaches this many minutes started; below it is cameo/rotation
# noise. Same cut as `calibration_analysis.py`'s "starters only" slice, so the
# two tables can be read against each other.
STARTER_MINUTES = 60.0

# Two-sided 5% critical values for Student's t. df=19 -> 2.09 is the number the
# A2 analysis quotes, so this table reproduces it exactly rather than reaching
# for scipy (which is an optional extra here).
_T_CRIT_95: Mapping[int, float] = {
    1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31,
    9: 2.26, 10: 2.23, 11: 2.20, 12: 2.18, 13: 2.16, 14: 2.14, 15: 2.13,
    16: 2.12, 17: 2.11, 18: 2.10, 19: 2.09, 20: 2.09, 21: 2.08, 22: 2.07,
    23: 2.07, 24: 2.06, 25: 2.06, 26: 2.06, 27: 2.05, 28: 2.05, 29: 2.05,
    30: 2.04,
}
_T_CRIT_LARGE = 1.96  # df > 30: the normal approximation

# How many "FPL's ep_next beat us by the most" rows the log names. The point is a
# short, actionable list to interrogate, not a full dump.
TOP_EP_ROWS = 5

TRIPLE_CAPTAIN = "triple_captain"
BENCH_BOOST = "bench_boost"


class PointInTimeError(RuntimeError):
    """Raised when no projections snapshot predates the gameweek deadline.

    Refusing is the correct behaviour: a calibration loop fed a post-deadline
    snapshot reports the model's hindsight, not its foresight.
    """


class PointInTimeWarning(UserWarning):
    """Warned when a snapshot is rejected as post-deadline, or when the
    point-in-time guarantee could not be verified at all."""


# ------------------------------------------------------------------ statistics


@dataclass(frozen=True)
class ErrorStats:
    """One cohort's prediction error (error = actual - predicted).

    `t` is the one-sample t against zero using the SAMPLE std (std/sqrt(n)) —
    the convention `calibration_analysis.py` established — and `significant`
    compares |t| with the two-sided 5% critical value at df = n-1. It is there to
    tell NOISE from BIAS: a +4/GW mean that fails this test is not a bias you may
    calibrate away, which is precisely how the A2 defect was closed.
    """

    label: str
    n: int
    mean_error: float
    mae: float
    std: float
    se: float
    t: float
    significant: bool
    mean_predicted: float
    mean_actual: float


def _t_critical(df: int) -> float:
    if df <= 0:
        return float("inf")
    return _T_CRIT_95.get(df, _T_CRIT_LARGE)


def error_stats(errors: Sequence[float], label: str,
                predicted: Sequence[float] | None = None,
                actual: Sequence[float] | None = None) -> ErrorStats:
    """Mean / MAE / spread / t for a sequence of per-observation errors."""
    values = [float(e) for e in errors if not (isinstance(e, float) and math.isnan(e))]
    n = len(values)
    if n == 0:
        return ErrorStats(label, 0, float("nan"), float("nan"), float("nan"),
                          float("nan"), float("nan"), False, float("nan"), float("nan"))
    mean = st.mean(values)
    mae = st.mean([abs(v) for v in values])
    std = st.pstdev(values)  # population std of the sample, as in the A2 script
    se = st.stdev(values) / math.sqrt(n) if n > 1 else float("nan")
    t = mean / se if se and not math.isnan(se) else float("nan")
    sig = bool(not math.isnan(t) and abs(t) >= _t_critical(n - 1))

    def _mean_of(seq: Sequence[float] | None) -> float:
        return st.mean([float(v) for v in seq]) if seq is not None and len(seq) else float("nan")

    return ErrorStats(
        label=label, n=n, mean_error=mean, mae=mae, std=std, se=se, t=t,
        significant=sig, mean_predicted=_mean_of(predicted), mean_actual=_mean_of(actual),
    )


def frame_stats(df: pd.DataFrame, label: str, error_col: str = "error") -> ErrorStats:
    """`error_stats` over a joined frame, carrying mean predicted/actual too."""
    pred_col = "ep_next" if error_col == "ep_error" else "predicted"
    return error_stats(
        df[error_col].tolist(), label,
        predicted=df[pred_col].tolist() if pred_col in df.columns else None,
        actual=df["actual"].tolist() if "actual" in df.columns else None,
    )


def cohort_stats(df: pd.DataFrame, prefix: str = "", error_col: str = "error") -> list[ErrorStats]:
    """ALL + one row per position, in a stable order."""
    out = [frame_stats(df, f"{prefix}ALL", error_col)]
    for pos in POSITIONS:
        sub = df[df["position"] == pos]
        if len(sub):
            out.append(frame_stats(sub, f"{prefix}{pos}", error_col))
    return out


# ------------------------------------------------- point-in-time snapshot pick


@dataclass(frozen=True)
class SnapshotChoice:
    """Which projections CSV was used as the PREDICTED side, and whether its
    point-in-time property was actually verified.

    `rejected` names every candidate discarded for being dated after the
    deadline (or written after it on deadline day). `verified` is False only when
    no deadline was available to check against, or when the caller explicitly
    over-rode the guard — either way the log says so in plain text.
    """

    path: Path
    snapshot_date: date | None
    deadline: datetime | None
    rejected: tuple[str, ...] = ()
    verified: bool = True
    note: str = ""


def _parse_snapshot_date(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return None


def _mtime_utc(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _is_post_deadline(path: Path, snap_date: date, deadline: datetime) -> bool:
    """A snapshot leaks the future if it is dated after the deadline day, or is
    dated ON the deadline day but was written after the deadline itself (the
    filename carries only a date, so deadline-day files need the mtime check)."""
    if snap_date > deadline.date():
        return True
    if snap_date == deadline.date():
        return _mtime_utc(path) > deadline
    return False


def select_snapshot(
    deadline: datetime | None,
    projections_dir: Path | None = None,
    explicit: Path | None = None,
    allow_post_deadline: bool = False,
) -> SnapshotChoice:
    """The newest `db/projections/YYYY-MM-DD.csv` at or before `deadline`.

    Never silently reaches past the deadline: post-deadline candidates are
    rejected, named in the returned `SnapshotChoice`, and warned about
    (`PointInTimeWarning`). If nothing qualifies, raises `PointInTimeError`
    unless `allow_post_deadline` is set — in which case the newest file is used
    and the choice is flagged `verified=False` so the log carries the caveat.
    """
    if explicit is not None:
        snap_date = _parse_snapshot_date(explicit)
        if deadline is None:
            warnings.warn(
                f"no deadline available: cannot verify {explicit.name} predates GW kickoff",
                PointInTimeWarning, stacklevel=2,
            )
            return SnapshotChoice(explicit, snap_date, None, verified=False,
                                  note="no deadline supplied — point-in-time NOT verified")
        if snap_date is not None and _is_post_deadline(explicit, snap_date, deadline):
            msg = f"{explicit.name} was written AFTER the deadline {deadline.isoformat()}"
            if not allow_post_deadline:
                raise PointInTimeError(
                    f"{msg}; refusing to calibrate against a snapshot that saw the result"
                )
            warnings.warn(f"{msg} — used anyway (--allow-post-deadline)",
                          PointInTimeWarning, stacklevel=2)
            return SnapshotChoice(explicit, snap_date, deadline, rejected=(),
                                  verified=False, note="post-deadline snapshot forced by caller")
        return SnapshotChoice(explicit, snap_date, deadline)

    directory = projections_dir or PROJECTIONS_DIR
    dated: list[tuple[date, Path]] = []
    for path in sorted(Path(directory).glob("*.csv")):
        snap_date = _parse_snapshot_date(path)
        if snap_date is not None:
            dated.append((snap_date, path))
    if not dated:
        raise PointInTimeError(f"no YYYY-MM-DD.csv projections snapshots under {directory}")

    if deadline is None:
        snap_date, path = max(dated)
        warnings.warn(
            f"no deadline available: {path.name} chosen as newest, point-in-time NOT verified",
            PointInTimeWarning, stacklevel=2,
        )
        return SnapshotChoice(path, snap_date, None, verified=False,
                              note="no deadline supplied — point-in-time NOT verified")

    eligible = [(d, p) for d, p in dated if not _is_post_deadline(p, d, deadline)]
    rejected = tuple(p.name for d, p in dated if _is_post_deadline(p, d, deadline))
    if rejected:
        warnings.warn(
            f"rejected {len(rejected)} post-deadline projections snapshot(s) "
            f"({', '.join(rejected)}) for deadline {deadline.isoformat()}",
            PointInTimeWarning, stacklevel=2,
        )
    if not eligible:
        if not allow_post_deadline:
            raise PointInTimeError(
                f"no projections snapshot at or before {deadline.isoformat()} in {directory}; "
                f"only post-deadline files {rejected} exist — refusing to leak the future"
            )
        snap_date, path = max(dated)
        return SnapshotChoice(path, snap_date, deadline, rejected=rejected, verified=False,
                              note="post-deadline snapshot forced by caller")
    snap_date, path = max(eligible)
    return SnapshotChoice(path, snap_date, deadline, rejected=rejected)


# ------------------------------------------------------------- predicted side


def predicted_column(gw: int) -> str:
    return f"xpts_gw{gw}"


def load_predictions(path: Path, gw: int) -> pd.DataFrame:
    """Predicted side for GW n from a projections CSV.

    Returns `id, web_name, team, position, price, predicted, ep_next,
    exp_minutes_gw`. `ep_next` stays NaN when the snapshot carried none (the
    backtest archive has no point-in-time FPL prediction) — never filled with a
    fake 0.0, which would silently flatter the benchmark.
    """
    df = pd.read_csv(path)
    col = predicted_column(gw)
    if col not in df.columns:
        raise KeyError(
            f"{path.name} has no {col!r} column — that snapshot's horizon does not "
            f"cover GW{gw} (columns: {[c for c in df.columns if c.startswith('xpts_gw')]})"
        )
    out = pd.DataFrame(
        {
            "id": df["id"].astype(int),
            "web_name": df.get("web_name", pd.Series(dtype=object)),
            "team": df.get("team", pd.Series(dtype=object)),
            "position": df.get("position", pd.Series(dtype=object)),
            "price": df.get("price", pd.Series(dtype=float)),
            "predicted": df[col].astype(float),
            "ep_next": pd.to_numeric(df.get("ep_next"), errors="coerce")
            if "ep_next" in df.columns
            else float("nan"),
            "exp_minutes_gw": pd.to_numeric(df.get("exp_minutes_gw"), errors="coerce")
            if "exp_minutes_gw" in df.columns
            else float("nan"),
        }
    )
    return out.drop_duplicates("id").reset_index(drop=True)


# ---------------------------------------------------------------- actual side
# Both actual sources go through one narrow seam — a callable returning a frame
# of `id, actual, minutes` — so tests never need the network and the live path is
# a one-line substitution.

ActualsFetcher = Callable[[int], pd.DataFrame]


def live_actuals(gw: int, fetch: Callable[[int], dict] | None = None) -> pd.DataFrame:
    """Actuals for a finished/live GW from `event/{gw}/live` (FPL API).

    `fetch` is injectable purely so tests can hand in a canned payload; the
    default is the real read-only client.
    """
    payload = (fetch or get_event_live)(gw)
    rows = [
        {
            "id": int(element["id"]),
            "actual": float(element.get("stats", {}).get("total_points", 0) or 0),
            "minutes": float(element.get("stats", {}).get("minutes", 0) or 0),
        }
        for element in payload.get("elements", [])
    ]
    return pd.DataFrame(rows, columns=["id", "actual", "minutes"])


def backtest_actuals(path: Path) -> pd.DataFrame:
    """Actuals (and squad roles) from a committed backtest `gw{NN}_players.csv`.

    Those files cover the 15 we OWNED only, so a backtest run has no whole-pool
    cohort — the log states that rather than pretending otherwise.
    """
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "id": df["id"].astype(int),
            "actual": df["actual"].astype(float),
            "minutes": pd.to_numeric(df.get("minutes"), errors="coerce"),
        }
    )
    if "role" in df.columns:
        out["role"] = df["role"]
    return out.drop_duplicates("id").reset_index(drop=True)


def load_squad(path: Path) -> pd.DataFrame:
    """Squad roles for a LIVE gameweek: a CSV with `id` and `role` (C/V/XI/bench)."""
    df = pd.read_csv(path)
    missing = {"id", "role"} - set(df.columns)
    if missing:
        raise KeyError(f"{path.name} needs columns id, role (missing {sorted(missing)})")
    return pd.DataFrame({"id": df["id"].astype(int), "role": df["role"].astype(str)})


# ------------------------------------------------------------------ the join


@dataclass(frozen=True)
class JoinReport:
    """How the id join landed. A player present on one side only is DROPPED from
    the metrics and counted here — a silent drop is how a calibration loop
    quietly starts measuring a different population than it claims to."""

    matched: int
    predicted_only: int
    actual_only: int
    predicted_only_names: tuple[str, ...] = ()


def join_predicted_actual(
    predicted: pd.DataFrame, actual: pd.DataFrame
) -> tuple[pd.DataFrame, JoinReport]:
    """Inner-join on the FPL player id and attach `error = actual - predicted`."""
    merged = predicted.merge(actual, on="id", how="inner")
    merged["error"] = merged["actual"] - merged["predicted"]
    merged["ep_error"] = merged["actual"] - merged["ep_next"]
    pred_ids, act_ids = set(predicted["id"]), set(actual["id"])
    orphan = predicted[predicted["id"].isin(pred_ids - act_ids)]
    report = JoinReport(
        matched=len(merged),
        predicted_only=len(pred_ids - act_ids),
        actual_only=len(act_ids - pred_ids),
        predicted_only_names=tuple(str(n) for n in orphan["web_name"].head(10)),
    )
    return merged.reset_index(drop=True), report


# ----------------------------------------------------- base XI / captain slot


@dataclass(frozen=True)
class SlotSplit:
    """The owned XI's predicted and actual points split into BASE XI + CAPTAIN
    SLOT, matching `backtest.simulate.XiBreakdown` exactly: the base excludes the
    captain entirely and the captain slot carries all `captain_mult` copies of
    him, so `base + slot == total` and no player is double-counted.

    The `xi_capx1_* / captain_extra_*` fields are the other cut of the SAME
    total, the one `reports/backtest/2025-26/calibration.md` headlines (XI with
    the captain counted once, plus the doubled EXTRA copy). Both are reported
    because the A2 finding is stated in the second and the memo prints the first.

    Pre-autosub and pre-hit: those are squad-accounting wedges, not prediction
    error (see the module docstring).
    """

    captain_id: int
    captain_name: str
    effective_captain_id: int
    effective_captain_name: str
    captain_mult: int
    counted: int
    base_xi_predicted: float
    base_xi_actual: float
    captain_slot_predicted: float
    captain_slot_actual: float
    xi_capx1_predicted: float
    xi_capx1_actual: float
    captain_extra_predicted: float
    captain_extra_actual: float

    @property
    def base_xi_error(self) -> float:
        return self.base_xi_actual - self.base_xi_predicted

    @property
    def captain_slot_error(self) -> float:
        return self.captain_slot_actual - self.captain_slot_predicted

    @property
    def total_predicted(self) -> float:
        return self.base_xi_predicted + self.captain_slot_predicted

    @property
    def total_actual(self) -> float:
        return self.base_xi_actual + self.captain_slot_actual

    @property
    def total_error(self) -> float:
        return self.total_actual - self.total_predicted

    @property
    def xi_capx1_error(self) -> float:
        return self.xi_capx1_actual - self.xi_capx1_predicted

    @property
    def captain_extra_error(self) -> float:
        return self.captain_extra_actual - self.captain_extra_predicted

    @property
    def captain_switched(self) -> bool:
        return self.effective_captain_id != self.captain_id


def slot_split(owned: pd.DataFrame, chip: str | None = None) -> SlotSplit | None:
    """Split the owned, fielded players into base XI + captain slot.

    `owned` carries `role` (C/V/XI/bench) alongside predicted/actual/minutes.
    Counted players are the XI, or all 15 on a bench boost. The captain is
    doubled (tripled on a triple captain); the EFFECTIVE captain is the vice when
    the captain records zero minutes, matching the FPL rule and the A2 script.
    """
    if "role" not in owned.columns:
        return None
    captains = owned[owned["role"] == CAPTAIN_ROLE]
    if not len(captains):
        return None
    cap = captains.iloc[0]
    counted = owned if chip == BENCH_BOOST else owned[owned["role"].isin(XI_ROLES)]
    mult = 3 if chip == TRIPLE_CAPTAIN else 2

    eff = cap
    if float(cap.get("minutes") or 0) <= 0:
        vices = owned[owned["role"] == VICE_ROLE]
        if len(vices) and float(vices.iloc[0].get("minutes") or 0) > 0:
            eff = vices.iloc[0]

    non_cap = counted[counted["id"] != int(cap["id"])]
    base_pred = float(non_cap["predicted"].sum())
    base_act = float(non_cap["actual"].sum())
    cap_pred, cap_act = float(cap["predicted"]), float(eff["actual"])
    return SlotSplit(
        captain_id=int(cap["id"]),
        captain_name=str(cap.get("web_name", cap["id"])),
        effective_captain_id=int(eff["id"]),
        effective_captain_name=str(eff.get("web_name", eff["id"])),
        captain_mult=mult,
        counted=len(counted),
        base_xi_predicted=base_pred,
        base_xi_actual=base_act,
        captain_slot_predicted=mult * cap_pred,
        captain_slot_actual=mult * cap_act,
        xi_capx1_predicted=base_pred + cap_pred,
        xi_capx1_actual=base_act + cap_act,
        captain_extra_predicted=(mult - 1) * cap_pred,
        captain_extra_actual=(mult - 1) * cap_act,
    )


# ------------------------------------------------------------ ep_next benchmark


@dataclass(frozen=True)
class Benchmark:
    """Our projection vs FPL's `ep_next` over the rows where BOTH exist.

    `n` is the NaN-dropped sample — the backtest archive carries no point-in-time
    `ep_next` at all, so this is routinely 0 and the log says "absent" rather
    than inventing a comparison.
    """

    n: int
    ours: ErrorStats
    fpl: ErrorStats
    ours_closer: int
    fpl_closer: int
    ties: int
    fpl_wins: pd.DataFrame = field(default_factory=pd.DataFrame)


def benchmark_ep_next(joined: pd.DataFrame, top: int = TOP_EP_ROWS) -> Benchmark:
    """Side-by-side error for our `xpts_gw{n}` and FPL's `ep_next`."""
    both = joined[joined["ep_next"].notna() & joined["error"].notna()].copy()
    if not len(both):
        empty = error_stats([], "n/a")
        return Benchmark(0, empty, empty, 0, 0, 0, both)
    both["ours_abs"] = both["error"].abs()
    both["fpl_abs"] = both["ep_error"].abs()
    both["fpl_edge"] = both["ours_abs"] - both["fpl_abs"]  # >0 = FPL was closer
    wins = both[both["fpl_edge"] > 0].sort_values("fpl_edge", ascending=False).head(top)
    return Benchmark(
        n=len(both),
        ours=frame_stats(both, "ours (xpts_gw)"),
        fpl=frame_stats(both, "FPL ep_next", error_col="ep_error"),
        ours_closer=int((both["fpl_edge"] < 0).sum()),
        fpl_closer=int((both["fpl_edge"] > 0).sum()),
        ties=int((both["fpl_edge"] == 0).sum()),
        fpl_wins=wins,
    )


# ------------------------------------------------------------------ the result


@dataclass(frozen=True)
class GwCalibration:
    """Everything the review needs for one gameweek's calibration entry."""

    gw: int
    snapshot: SnapshotChoice
    actuals_source: str
    join: JoinReport
    joined: pd.DataFrame
    owned: pd.DataFrame
    pool_stats: list[ErrorStats]
    pool_started_stats: list[ErrorStats]
    owned_stats: list[ErrorStats]
    slots: SlotSplit | None
    benchmark: Benchmark
    chip: str | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def calibrate_gw(
    gw: int,
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    snapshot: SnapshotChoice,
    actuals_source: str,
    squad: pd.DataFrame | None = None,
    chip: str | None = None,
) -> GwCalibration:
    """Join one gameweek's predicted and actual sides and compute every cohort.

    `squad` (id, role) marks the players we OWNED. When the actuals frame already
    carries a `role` column (the backtest CSVs do) it is used directly, so a
    backtest run needs no extra input.
    """
    joined, report = join_predicted_actual(predictions, actuals)
    if squad is not None and "role" not in joined.columns:
        joined = joined.merge(squad, on="id", how="left")
    owned = joined[joined["role"].notna()] if "role" in joined.columns else joined.iloc[0:0]

    started = joined[joined["minutes"].fillna(0) >= STARTER_MINUTES]
    return GwCalibration(
        gw=gw,
        snapshot=snapshot,
        actuals_source=actuals_source,
        join=report,
        joined=joined,
        owned=owned,
        pool_stats=cohort_stats(joined),
        pool_started_stats=cohort_stats(started),
        owned_stats=cohort_stats(owned) if len(owned) else [],
        slots=slot_split(owned, chip=chip) if len(owned) else None,
        benchmark=benchmark_ep_next(joined),
        chip=chip,
    )


# ------------------------------------------------------------------- markdown

LOG_HEADER = """# Calibration log — predicted vs actual, per gameweek

*Generated by `python -m fpl_claude.reports.calibration --gw N` (backlog A3) and
consumed by `/fpl-review` step 5. **Append-only**: one section per gameweek, never
edited or reordered — like `db/`, this is history, and the point of it is that we
can always ask "what did the model predict BEFORE GW n" (CLAUDE.md).*

**Error convention: `error = actual − predicted`** — a POSITIVE error means the
model UNDER-predicted. Same convention as `notebooks/calibration_analysis.py` and
`reports/backtest/2025-26/calibration.md`, so the live weeks read against the
closed 20-GW backtest decomposition directly.

**How to read the slot table.** The 2025/26 decomposition (A2) found the residual
is *not* captain-only: the small mean under-prediction (+4.3/GW) lives in the
**base XI** and is inside sampling noise (t = 1.47, ns), while the **doubled
captain slot** is mean-*unbiased* (−0.07) and merely high-variance. Base XI and
captain slot are therefore logged apart, in both cuts of the same total: the memo
cut (base = XI *excluding* the captain, slot = captain × his multiplier) and the
A2 headline cut (XI with the captain counted once, plus the doubled extra copy).
Auto-subs and hits are squad-accounting wedges, not prediction error, and are not
in these numbers.

**`ep_next`** is FPL's own next-GW prediction, carried as an independent
benchmark. Where it beat us, ask what it saw — usually minutes or a set-piece /
penalty role — and feed that into the overlay or a model TODO.
"""


def _fmt(value: float, places: int = 2, signed: bool = False) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:+.{places}f}" if signed else f"{value:.{places}f}"


def _stats_table(rows: Sequence[ErrorStats]) -> list[str]:
    out = [
        "| cohort | n | mean pred | mean act | mean err | MAE | std | SE | t | sig 5% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        out.append(
            f"| {r.label} | {r.n} | {_fmt(r.mean_predicted)} | {_fmt(r.mean_actual)} | "
            f"{_fmt(r.mean_error, signed=True)} | {_fmt(r.mae)} | {_fmt(r.std)} | "
            f"{_fmt(r.se)} | {_fmt(r.t, signed=True)} | {'**yes**' if r.significant else 'no'} |"
        )
    return out


def _snapshot_lines(cal: GwCalibration) -> list[str]:
    snap = cal.snapshot
    try:
        shown = snap.path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        shown = snap.path.name
    deadline = snap.deadline.isoformat() if snap.deadline else "unknown"
    verdict = (
        "point-in-time **verified** (written at or before the deadline)"
        if snap.verified
        else f"point-in-time **NOT verified** — {snap.note or 'see warnings'}"
    )
    lines = [
        (
            f"- **Predicted side:** `{shown}` (column `{predicted_column(cal.gw)}`), "
            f"GW{cal.gw} deadline `{deadline}` — {verdict}."
        ),
        f"- **Actual side:** {cal.actuals_source}.",
        (
            f"- **Join (FPL player id):** {cal.join.matched} matched | "
            f"{cal.join.predicted_only} projected-but-no-actual | "
            f"{cal.join.actual_only} actual-but-not-projected."
        ),
    ]
    if snap.rejected:
        lines.append(
            f"- **Rejected as post-deadline:** {', '.join(f'`{r}`' for r in snap.rejected)} "
            "(never used — a snapshot that saw the result cannot calibrate it)."
        )
    if cal.chip:
        lines.append(f"- **Chip played:** `{cal.chip}`.")
    return lines


def _slot_lines(slots: SlotSplit) -> list[str]:
    cap = f"{slots.captain_name} ×{slots.captain_mult}"
    if slots.captain_switched:
        cap += f" (armband fell to {slots.effective_captain_name})"
    return [
        "",
        "### Owned XI — base XI vs captain slot",
        "",
        "| slot | predicted | actual | error |",
        "|---|---:|---:|---:|",
        (
            f"| base XI ({slots.counted - 1}, captain excluded) "
            f"| {_fmt(slots.base_xi_predicted)} | {_fmt(slots.base_xi_actual)} "
            f"| {_fmt(slots.base_xi_error, signed=True)} |"
        ),
        (
            f"| captain slot ({cap}) | {_fmt(slots.captain_slot_predicted)} "
            f"| {_fmt(slots.captain_slot_actual)} "
            f"| {_fmt(slots.captain_slot_error, signed=True)} |"
        ),
        (
            f"| **total** | **{_fmt(slots.total_predicted)}** "
            f"| **{_fmt(slots.total_actual)}** "
            f"| **{_fmt(slots.total_error, signed=True)}** |"
        ),
        (
            f"| *A2 cut:* XI incl. captain ×1 | {_fmt(slots.xi_capx1_predicted)} "
            f"| {_fmt(slots.xi_capx1_actual)} | {_fmt(slots.xi_capx1_error, signed=True)} |"
        ),
        (
            f"| *A2 cut:* captain extra copies | {_fmt(slots.captain_extra_predicted)} "
            f"| {_fmt(slots.captain_extra_actual)} "
            f"| {_fmt(slots.captain_extra_error, signed=True)} |"
        ),
    ]


def _benchmark_lines(bench: Benchmark) -> list[str]:
    lines = ["", "### FPL `ep_next` benchmark", ""]
    if bench.n == 0:
        lines.append(
            "`ep_next` absent from this snapshot (NaN for every joined player) — no "
            "external benchmark this week. The backtest archive has no point-in-time "
            "FPL prediction; live snapshots do."
        )
        return lines
    lines += _stats_table([bench.ours, bench.fpl])
    lines += [
        "",
        (
            f"Closer on {bench.n} shared players: **ours {bench.ours_closer}**, "
            f"FPL {bench.fpl_closer}, ties {bench.ties}."
        ),
    ]
    if len(bench.fpl_wins):
        lines += [
            "",
            (
                "Where FPL's number beat ours by the most — *ask what it saw "
                "(minutes? set-piece/penalty duty?)*:"
            ),
            "",
            "| player | pos | ours | ep_next | actual | our err | FPL err |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for _, r in bench.fpl_wins.iterrows():
            lines.append(
                f"| {r['web_name']} | {r['position']} | {_fmt(float(r['predicted']))} | "
                f"{_fmt(float(r['ep_next']))} | {_fmt(float(r['actual']), 0)} | "
                f"{_fmt(float(r['error']), signed=True)} | "
                f"{_fmt(float(r['ep_error']), signed=True)} |"
            )
    return lines


def render_section(cal: GwCalibration) -> str:
    """The markdown block appended to the log for one gameweek."""
    lines = [
        f"## GW{cal.gw} — logged {cal.generated_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        *_snapshot_lines(cal),
    ]
    if cal.slots is not None:
        lines += _slot_lines(cal.slots)
    if cal.owned_stats:
        lines += ["", "### Owned squad — per-player error", ""] + _stats_table(cal.owned_stats)
    else:
        lines += [
            "",
            (
                "*No squad supplied — pool metrics only "
                "(pass `--squad` or `--backtest-players`).*"
            ),
        ]
    lines += ["", "### Whole player pool — per-player error", ""]
    if len(cal.owned) and len(cal.owned) == len(cal.joined):
        lines += [
            (
                "*Every joined player was owned — the backtest archive stores the 15 we "
                "held, so there is no wider-pool cut this week. A live gameweek joins the "
                "whole projected pool and the two tables diverge.*"
            ),
            "",
        ]
    lines += _stats_table(cal.pool_stats)
    if cal.pool_started_stats:
        lines += [
            "",
            (
                f"Starters only (minutes ≥ {STARTER_MINUTES:.0f}) — isolates scoring-rate "
                "level from minutes risk:"
            ),
            "",
        ] + _stats_table(cal.pool_started_stats)
    lines += _benchmark_lines(cal.benchmark)
    lines += ["", "---", ""]
    return "\n".join(lines)


def append_log(cal: GwCalibration, path: Path | None = None) -> Path:
    """Append one GW section to the calibration log, creating it with the header
    if absent. NEVER rewrites or removes prior content: a re-run for a gameweek
    already logged appends a fresh section (and says so), because the audit trail
    is the deliverable — the newest section for a GW is the current one."""
    target = Path(path or DEFAULT_LOG)
    target.parent.mkdir(parents=True, exist_ok=True)
    section = render_section(cal)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if f"## GW{cal.gw} —" in existing:
            section = section.replace(
                "\n\n- **Predicted side:**",
                f"\n\n*Re-log: a GW{cal.gw} section already exists above; this one supersedes "
                "it. Earlier sections are kept — the log is append-only.*\n\n- **Predicted "
                "side:**",
                1,
            )
        body = existing if existing.endswith("\n") else existing + "\n"
        target.write_text(body + "\n" + section + "\n", encoding="utf-8")
    else:
        target.write_text(LOG_HEADER + "\n---\n\n" + section + "\n", encoding="utf-8")
    return target


# ------------------------------------------------------------------------ CLI


def _load_bootstrap(from_snapshot: str | None) -> dict | None:
    if from_snapshot:
        path = RAW_DIR / from_snapshot / "bootstrap.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None
    try:
        return get_bootstrap()
    except OSError:  # offline / egress-blocked: fall back to --deadline
        return None


def deadline_for_gw(gw: int, bootstrap: Mapping[str, Any] | None) -> datetime | None:
    """The GW's deadline as an aware UTC datetime, from a bootstrap payload."""
    if not bootstrap:
        return None
    for event in bootstrap.get("events", []):
        if int(event["id"]) == gw:
            # Python 3.11+ fromisoformat parses the API's trailing "Z" directly.
            return datetime.fromisoformat(str(event["deadline_time"]))
    return None


def _parse_deadline(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--gw", type=int, required=True, help="gameweek to calibrate")
    parser.add_argument("--actuals", choices=("live", "backtest"), default="live",
                        help="where the ACTUAL side comes from (default: live FPL API)")
    parser.add_argument("--backtest-players", type=Path, default=None,
                        help="gw{NN}_players.csv (required with --actuals backtest)")
    parser.add_argument("--projections-dir", type=Path, default=PROJECTIONS_DIR,
                        help="directory of YYYY-MM-DD.csv projections snapshots")
    parser.add_argument("--snapshot", type=Path, default=None,
                        help="use THIS projections CSV instead of selecting by deadline")
    parser.add_argument("--deadline", default=None,
                        help="GW deadline (ISO 8601, UTC assumed); else read from bootstrap")
    parser.add_argument("--from-snapshot", default=None,
                        help="db/raw/ date dir to read the deadline from, instead of the API")
    parser.add_argument("--squad", type=Path, default=None,
                        help="CSV of owned players for a live GW: id, role (C/V/XI/bench)")
    parser.add_argument("--chip", default=None,
                        help="chip played this GW (triple_captain / bench_boost / ...)")
    parser.add_argument("--out", type=Path, default=DEFAULT_LOG, help="calibration log path")
    parser.add_argument("--allow-post-deadline", action="store_true",
                        help="DANGEROUS: calibrate against a snapshot written after the deadline")
    parser.add_argument("--dry-run", action="store_true", help="print the section, do not append")
    args = parser.parse_args(argv)

    deadline = _parse_deadline(args.deadline)
    if deadline is None:
        deadline = deadline_for_gw(args.gw, _load_bootstrap(args.from_snapshot))

    snapshot = select_snapshot(
        deadline,
        projections_dir=args.projections_dir,
        explicit=args.snapshot,
        allow_post_deadline=args.allow_post_deadline,
    )
    predictions = load_predictions(snapshot.path, args.gw)

    if args.actuals == "backtest":
        if args.backtest_players is None:
            raise SystemExit("--actuals backtest requires --backtest-players PATH")
        actuals = backtest_actuals(args.backtest_players)
        source = f"backtest archive `{args.backtest_players.name}` (owned squad only)"
    else:
        actuals = live_actuals(args.gw)
        source = f"live FPL API (`event/{args.gw}/live`)"

    squad = load_squad(args.squad) if args.squad else None
    cal = calibrate_gw(
        args.gw, predictions, actuals, snapshot, source, squad=squad, chip=args.chip
    )

    if args.dry_run:
        print(render_section(cal))
        return
    path = append_log(cal, args.out)
    print(f"calibration appended: {path}")
    print(f"GW{args.gw}: snapshot {snapshot.path.name} | {cal.join.matched} players joined")
    if cal.slots is not None:
        s = cal.slots
        print(f"  base XI {_fmt(s.base_xi_error, signed=True)} | "
              f"captain slot {_fmt(s.captain_slot_error, signed=True)} | "
              f"total {_fmt(s.total_error, signed=True)}")


if __name__ == "__main__":
    main()

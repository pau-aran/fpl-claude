"""Cross-season bridge: last season's stats re-keyed to THIS season's player ids.

FPL reassigns element `id` every season. The projections pipeline feeds a prior
season's payload to `models.rates.from_bootstrap` and
`models.minutes.priors_from_bootstrap`, both of which join on `id` — so handing
last season's bootstrap straight to a new season's run silently attaches the
WRONG player's history to every row. It does not crash; it just lies. The stable
cross-season key is `code` (the player's permanent FPL code), and this module is
the only place we do that join for the LIVE pipeline
(`backtest/data.py::SeasonStore.prior_bootstrap` does the same job for the
point-in-time backtest; the two are deliberately not coupled).

Source of prior stats: vaastav/Fantasy-Premier-League `players_raw.csv` — the
final bootstrap dump of a completed season, which carries `code`.

Deliberate choice: players with NO prior row (summer signings, promoted-club
players, academy graduates) are DROPPED, not zero-filled. A zeroed prior reads
as "played and produced nothing", which is a lie that would drag a real player's
blended rates to the floor; an absent prior is honest, and the existing
`rates.blend` / `rates.shrink_newcomers` / `minutes._start_share` machinery
already handles priorless players as genuine unknowns (`low_sample`,
replacement-level regression, neutral start share).

CLI:
    python -m fpl_claude.data.season_bridge --from-snapshot 2026-07-25 \
        --season-csv db/vaastav/2025-26/players_raw.csv [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .fpl_api import PROJECT_ROOT, RAW_DIR

POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

# Every field the rates and minutes layers actually read off a prior payload:
#   rates.from_bootstrap  -> id, minutes, expected_goals, expected_assists,
#                            saves, defensive_contribution, bonus
#   minutes.priors_from_bootstrap -> id, starts
# element_type/web_name/code are carried for diagnostics and coverage reporting,
# not consumed by the model layers.
COUNT_COLUMNS = ("minutes", "starts")
FLOAT_COLUMNS = (
    "expected_goals",
    "expected_assists",
    "saves",
    "defensive_contribution",
    "bonus",
)
REQUIRED_CSV_COLUMNS = ("code", "element_type", *COUNT_COLUMNS)


def _stat(value: Any) -> float:
    """CSV blanks arrive as NaN; NaN must become 0.0 or every per-90 downstream
    turns into NaN and the whole projection for that player is silently void.

    Note this is the ABSENCE of a stat within a row we do have (e.g.
    `defensive_contribution` did not exist before 2025/26), which is genuinely
    zero contribution under that scoring category — quite different from the
    absence of the whole ROW, which is handled by dropping the player."""
    if value is None:
        return 0.0
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(out) else out


def _count(value: Any) -> int:
    return int(_stat(value))


@dataclass
class Coverage:
    """How much of the current squad actually got a prior — the number that
    decides whether a pre-season projection is evidence or vibes."""

    season_csv: str
    total_players: int
    matched_players: int
    by_position: dict[str, tuple[int, int]] = field(default_factory=dict)  # pos -> (n, total)
    by_team: dict[str, tuple[int, int]] = field(default_factory=dict)  # team -> (n, total)

    @property
    def pct(self) -> float:
        return 100.0 * self.matched_players / self.total_players if self.total_players else 0.0

    def to_text(self) -> str:
        """ASCII-only summary (the Windows console is cp1252 — never print
        player names from here)."""
        lines = [
            f"prior source: {self.season_csv}",
            f"coverage: {self.matched_players}/{self.total_players} ({self.pct:.1f}%)",
            "",
            "by position:",
        ]
        for pos in ("GKP", "DEF", "MID", "FWD"):
            if pos in self.by_position:
                n, tot = self.by_position[pos]
                lines.append(f"  {pos}  {n:3d}/{tot:3d}  ({100.0 * n / tot:5.1f}%)")
        lines += ["", "by club:"]
        for team, (n, tot) in sorted(self.by_team.items(), key=lambda kv: kv[1][0] / kv[1][1]):
            lines.append(f"  {team:<16} {n:3d}/{tot:3d}  ({100.0 * n / tot:5.1f}%)")
        return "\n".join(lines)


def load_prior_players(season_csv_path: str | Path) -> pd.DataFrame:
    """A completed season's players_raw.csv, validated for the columns we need."""
    path = Path(season_csv_path)
    df = pd.read_csv(path, encoding="utf-8")
    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing required column(s) {missing}")
    if df["code"].duplicated().any():
        # Two rows for one code would make the remap ambiguous; keep the one
        # with the most minutes (the real season, not a duplicate stub).
        df = df.sort_values("minutes", ascending=False).drop_duplicates("code", keep="first")
    return df


def prior_bootstrap_from_vaastav(
    current_bootstrap: dict[str, Any],
    season_csv_path: str | Path,
    min_minutes: int = 0,
) -> dict[str, Any]:
    """Prior-season stats as a bootstrap-shaped payload keyed by CURRENT ids.

    Join is on `code` (stable across seasons); players in the current bootstrap
    with no prior row are absent from the result, players in the prior season
    who are no longer in the game (relegated/departed) are dropped too.

    `min_minutes` drops prior rows too thin to be evidence. A row is not the
    same as a sample: a player who spent last season injured or out on loan has
    a row of zeros, and `rates.blend` will hand him that all-zero prior at FULL
    weight pre-season (current minutes are 0, so the prior gets weight 1) while
    `has_prior=True` makes `shrink_newcomers` skip him — so he projects as a
    confident zero rather than as an unknown. Raising this threshold routes
    those players into the priorless path, where they are flagged `low_sample`
    and regressed to a replacement baseline instead.

    DEFAULT 0 (keep every row) IS DELIBERATE. A blanket threshold is an
    investigative knob, not the fix: at 450 it rescues the injured starters
    (G.Jesus, Chiesa) but it also promotes genuine backup keepers who played
    little because they were BENCHED, not hurt — Arrizabalaga +9.5 xPts,
    Trafford +7.2, Benitez +7.1 over an 8-GW horizon, all of them wrong.
    "Few minutes" has two causes and the prior cannot tell them apart; the real
    fix belongs in the minutes model. Evidence and numbers:
    research/2026-27/projections-run.md.
    """
    prior = load_prior_players(season_csv_path)
    code_to_id = {int(p["code"]): int(p["id"]) for p in current_bootstrap["elements"]}

    elements: list[dict[str, Any]] = []
    for row in prior.to_dict("records"):
        pid = code_to_id.get(int(row["code"]))
        if pid is None:
            continue  # no longer in the game this season
        if _count(row.get("minutes")) < min_minutes:
            continue  # too thin to be evidence — treat as priorless, not as zero
        element = {
            "id": pid,
            "code": int(row["code"]),
            "web_name": row.get("web_name"),
            "element_type": int(row["element_type"]),
            # The club those minutes were played FOR. `team_code` is stable
            # across seasons (team `id` is not), so the minutes layer can tell
            # "37 starts, same club" from "37 starts, somewhere else" — the
            # difference between a nailed starter and an unknown quantity.
            "team_code": _count(row.get("team_code")) or None,
        }
        element.update({c: _count(row.get(c)) for c in COUNT_COLUMNS})
        element.update({c: _stat(row.get(c)) for c in FLOAT_COLUMNS})
        elements.append(element)
    return {"elements": elements, "source": str(season_csv_path)}


def coverage(
    current_bootstrap: dict[str, Any], prior_bootstrap: dict[str, Any]
) -> Coverage:
    """Match rate of the remapped prior against the current squad, by position
    and by club. Promoted clubs should read near-zero — if one reads high, the
    join is matching the wrong thing and every number downstream is suspect."""
    teams = {int(t["id"]): t["name"] for t in current_bootstrap["teams"]}
    matched = {int(e["id"]) for e in prior_bootstrap["elements"]}

    by_position: dict[str, list[int]] = {}
    by_team: dict[str, list[int]] = {}
    for p in current_bootstrap["elements"]:
        hit = int(p["id"]) in matched
        pos = POSITION_BY_ELEMENT_TYPE.get(int(p["element_type"]), "?")
        team = teams.get(int(p["team"]), "?")
        for bucket, key in ((by_position, pos), (by_team, team)):
            counts = bucket.setdefault(key, [0, 0])
            counts[0] += int(hit)
            counts[1] += 1

    return Coverage(
        season_csv=str(prior_bootstrap.get("source", "?")),
        total_players=len(current_bootstrap["elements"]),
        matched_players=sum(
            1 for p in current_bootstrap["elements"] if int(p["id"]) in matched
        ),
        by_position={k: (v[0], v[1]) for k, v in by_position.items()},
        by_team={k: (v[0], v[1]) for k, v in by_team.items()},
    )


def _load_current(from_snapshot: str | None, bootstrap_path: str | None) -> dict[str, Any]:
    if bootstrap_path:
        return json.loads(Path(bootstrap_path).read_text(encoding="utf-8"))
    if from_snapshot:
        return json.loads(
            (RAW_DIR / from_snapshot / "bootstrap.json").read_text(encoding="utf-8")
        )
    from .fpl_api import get_bootstrap

    return get_bootstrap()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", help="db/raw/ date dir (YYYY-MM-DD)")
    parser.add_argument("--bootstrap", help="explicit path to a current bootstrap.json")
    parser.add_argument(
        "--season-csv",
        default=str(PROJECT_ROOT / "db" / "vaastav" / "2025-26" / "players_raw.csv"),
        help="prior season's players_raw.csv (must contain `code`)",
    )
    parser.add_argument(
        "--min-prior-minutes",
        type=int,
        default=0,
        help="drop prior rows below this many minutes (they are absence, not evidence)",
    )
    parser.add_argument("--out", help="write the remapped prior payload to this JSON path")
    args = parser.parse_args()

    current = _load_current(args.from_snapshot, args.bootstrap)
    prior = prior_bootstrap_from_vaastav(
        current, args.season_csv, min_minutes=args.min_prior_minutes
    )
    print(coverage(current, prior).to_text())

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(prior), encoding="utf-8")
        print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()

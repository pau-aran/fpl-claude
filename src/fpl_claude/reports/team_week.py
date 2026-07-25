"""Weekly all-team report builder.

Produces one markdown skeleton per PL team for the report week under
reports/weekly/{YYYY-WW}/, pre-filled with everything derivable from FPL API data:

  - PL results in the last 7 days (score, home/away)
  - PL fixtures in the next 14 days with difficulty; pre-season / empty windows fall
    back to the next scheduled fixtures ("opening run") so the file is never blank
  - flagged players: status, news text, chance of playing
  - biggest weekly price/ownership movers, diffed against the previous db/raw/ snapshot

The /fpl-team-week-report skill then enriches each skeleton via web/X search with:
  - non-PL matches played (UCL/UEL/UECL, FA Cup, EFL Cup) and minutes distribution
  - pre-season: friendlies, confirmed transfers, manager/tactical shape
  - injuries picked up/cleared beyond FPL flags, press-conference notes
  - rotation-risk implications for FPL assets

Point-in-time guarantee: with --from-snapshot the report week, the "now" used for the
7d/14d windows and the movers baseline all come from the SNAPSHOT date, never from the
wall clock — so an old snapshot reconstructs the report as it would have been written.

CLI:  python -m fpl_claude.reports.team_week [--from-snapshot YYYY-MM-DD] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from ..data.fpl_api import PROJECT_ROOT, RAW_DIR, get_bootstrap, get_fixtures

REPORTS_DIR = PROJECT_ROOT / "reports" / "weekly"
POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
STATUS_LABELS = {
    "a": None,  # available — not flagged
    "d": "DOUBTFUL",
    "i": "INJURED",
    "s": "SUSPENDED",
    "u": "UNAVAILABLE",
    "n": "NOT IN SQUAD",
}

LOOKBACK_DAYS = 7
LOOKAHEAD_DAYS = 14
OPENING_RUN_FIXTURES = 5  # fallback horizon when the 14-day window is empty
MOVERS_PER_TEAM = 3  # per direction, per metric
OWNERSHIP_MOVE_THRESHOLD = 0.3  # percentage points — below this is noise

# Letters NFKD will not decompose (they are letters in their own right, not accents).
_TRANSLITERATE = str.maketrans(
    {"Ø": "O", "ø": "o", "Đ": "D", "đ": "d", "Ł": "L", "ł": "l",
     "Æ": "Ae", "æ": "ae", "Œ": "Oe", "œ": "oe", "ß": "ss", "Þ": "Th", "þ": "th"}
)


# --------------------------------------------------------------------------- io


def _read_json(path: Path):
    """Always UTF-8: FPL payloads and player names are not cp1252-safe."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    """Always UTF-8 + LF: reports carry Ødegaard/Šeško/Núñez and land in git."""
    path.write_text(text, encoding="utf-8", newline="\n")


def _parse_utc(raw) -> datetime:
    """ISO-8601 (with or without a trailing Z) -> tz-aware UTC datetime."""
    stamp = datetime.fromisoformat(str(raw))
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def _snapshot_instant(day_dir: Path, snapshot_date: date) -> datetime:
    """The moment the snapshot was taken (meta.json), else midday UTC of its date."""
    meta_file = day_dir / "meta.json"
    if meta_file.exists():
        fetched = (_read_json(meta_file) or {}).get("fetched_at_utc")
        if fetched:
            return _parse_utc(fetched)
    return datetime.combine(snapshot_date, time(12, 0), tzinfo=UTC)


def _load(
    from_snapshot: str | None, raw_dir: Path | None = None
) -> tuple[dict, list[dict], datetime, Path | None]:
    """Return (bootstrap, fixtures, as-of instant, snapshot dir used or None)."""
    root = raw_dir or RAW_DIR
    if from_snapshot:
        day_dir = root / from_snapshot
        bootstrap = _read_json(day_dir / "bootstrap.json")
        fixtures_file = day_dir / "fixtures.json"
        fixtures = _read_json(fixtures_file) if fixtures_file.exists() else []
        as_of = _snapshot_instant(day_dir, date.fromisoformat(from_snapshot))
        return bootstrap, fixtures, as_of, day_dir
    return get_bootstrap(), get_fixtures(), datetime.now(UTC), None


# ------------------------------------------------------------------- primitives


def slugify(name: str, taken: set[str] | None = None, fallback: str = "team") -> str:
    """Filesystem-safe, ASCII-folded slug, de-duplicated against `taken`.

    "Nott'm Forest" -> nottm-forest; "Brighton & Hove" -> brighton-hove.
    A second team slugging to the same value gets -2, -3, ... rather than
    silently overwriting the first team's report.
    """
    folded = unicodedata.normalize("NFKD", name.translate(_TRANSLITERATE))
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = "".join(c for c in folded if c not in "'’.")  # Nott'm -> nottm
    slug = "".join(c.lower() if c.isalnum() and c.isascii() else "-" for c in folded)
    slug = "-".join(part for part in slug.split("-") if part) or fallback
    if taken is None:
        return slug
    candidate, n = slug, 1
    while candidate in taken:
        n += 1
        candidate = f"{slug}-{n}"
    taken.add(candidate)
    return candidate


def _kickoff(fixture: dict) -> datetime | None:
    ko = fixture.get("kickoff_time")
    if not ko:
        return None
    return _parse_utc(ko)


def season_started(bootstrap: dict, fixtures: list[dict]) -> bool:
    """False in pre-season: no event current/finished and no fixture kicked off."""
    for event in bootstrap.get("events") or []:
        if event.get("finished") or event.get("is_current"):
            return True
    return any(fx.get("finished") or fx.get("started") for fx in fixtures)


def _next_deadline(bootstrap: dict, now: datetime) -> tuple[int, datetime] | None:
    for event in bootstrap.get("events") or []:
        raw = event.get("deadline_time")
        if not raw:
            continue
        deadline = _parse_utc(raw)
        if deadline > now:
            return event["id"], deadline
    return None


# ----------------------------------------------------------------------- movers


def find_prior_snapshot(raw_dir: Path, as_of: date) -> Path | None:
    """Newest snapshot directory strictly older than `as_of` that has a bootstrap."""
    if not raw_dir.exists():
        return None
    candidates = []
    for day_dir in raw_dir.iterdir():
        if not day_dir.is_dir() or not (day_dir / "bootstrap.json").exists():
            continue
        try:
            day = date.fromisoformat(day_dir.name)
        except ValueError:
            continue
        if day < as_of:
            candidates.append((day, day_dir))
    if not candidates:
        return None
    return max(candidates)[1]


def _pct(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def movers_by_team(
    elements: list[dict], prior_elements: list[dict] | None
) -> dict[int, list[str]]:
    """Per-team price/ownership move lines vs the prior snapshot.

    Returns {} when there is no prior snapshot — callers render the "no baseline"
    line instead of inventing movement.
    """
    if prior_elements is None:
        return {}
    prior = {p["id"]: p for p in prior_elements}
    out: dict[int, list[dict]] = {}
    for p in elements:
        before = prior.get(p["id"])
        if before is None:
            out.setdefault(p["team"], []).append({"player": p, "new": True})
            continue
        d_price = (p.get("now_cost") or 0) - (before.get("now_cost") or 0)
        d_own = _pct(p.get("selected_by_percent")) - _pct(before.get("selected_by_percent"))
        if d_price or abs(d_own) >= OWNERSHIP_MOVE_THRESHOLD:
            out.setdefault(p["team"], []).append(
                {"player": p, "new": False, "d_price": d_price, "d_own": d_own}
            )

    lines_by_team: dict[int, list[str]] = {}
    for team_id, moves in out.items():
        lines: list[str] = []
        priced = [m for m in moves if not m["new"] and m["d_price"]]
        for m in sorted(priced, key=lambda m: -abs(m["d_price"]))[: MOVERS_PER_TEAM * 2]:
            p = m["player"]
            lines.append(
                f"- price {m['d_price']:+d} → £{p['now_cost'] / 10:.1f}m — **{p['web_name']}**"
                f" ({p['selected_by_percent']}% owned)"
            )
        owned = [
            m
            for m in moves
            if not m["new"] and abs(m.get("d_own", 0.0)) >= OWNERSHIP_MOVE_THRESHOLD
        ]
        for m in sorted(owned, key=lambda m: -abs(m["d_own"]))[:MOVERS_PER_TEAM]:
            p = m["player"]
            lines.append(
                f"- ownership {m['d_own']:+.1f}pp → {p['selected_by_percent']}%"
                f" — **{p['web_name']}**"
            )
        for m in [m for m in moves if m["new"]][:MOVERS_PER_TEAM]:
            p = m["player"]
            lines.append(
                f"- NEW in the game — **{p['web_name']}**"
                f" ({POSITION_BY_ELEMENT_TYPE.get(p.get('element_type'), '?')},"
                f" £{p.get('now_cost', 0) / 10:.1f}m)"
            )
        if lines:
            lines_by_team[team_id] = lines
    return lines_by_team


# ---------------------------------------------------------------------- builder


def _fixture_line(fx: dict, team_id: int, teams: dict[int, dict]) -> str:
    is_home = fx["team_h"] == team_id
    opponent = teams[fx["team_a"] if is_home else fx["team_h"]]
    difficulty = fx["team_h_difficulty"] if is_home else fx["team_a_difficulty"]
    venue = "H" if is_home else "A"
    gw = f"GW{fx['event']}" if fx.get("event") else "TBC"
    return f"- {gw} {_kickoff(fx):%a %d %b}: {opponent['name']} ({venue}, FDR {difficulty})"


def build_reports(
    from_snapshot: str | None = None,
    out_dir: Path | None = None,
    raw_dir: Path | None = None,
) -> Path:
    """Write one skeleton per team plus index.md; return the week directory."""
    root_raw = raw_dir or RAW_DIR
    bootstrap, fixtures, now, _snapshot_dir = _load(from_snapshot, root_raw)
    as_of = now.date()
    week_dir = (out_dir or REPORTS_DIR) / f"{as_of:%G-%V}"
    week_dir.mkdir(parents=True, exist_ok=True)

    teams = {t["id"]: t for t in bootstrap["teams"]}
    players_by_team: dict[int, list[dict]] = {}
    for p in bootstrap["elements"]:
        players_by_team.setdefault(p["team"], []).append(p)

    started = season_started(bootstrap, fixtures)
    deadline = _next_deadline(bootstrap, now)

    prior_dir = find_prior_snapshot(root_raw, as_of)
    prior_elements = None
    if prior_dir is not None:
        prior_elements = _read_json(prior_dir / "bootstrap.json").get("elements")
    movers = movers_by_team(bootstrap["elements"], prior_elements)
    movers_baseline = (
        f"vs snapshot `{prior_dir.name}`"
        if prior_dir is not None
        else "no prior snapshot in `db/raw/` — no baseline to diff against"
    )

    week_label = f"{as_of:%G-W%V}"
    used_slugs: set[str] = set()
    stamp = (
        f"snapshot `{from_snapshot}` ({now:%Y-%m-%d %H:%M} UTC)"
        if from_snapshot
        else f"live FPL API, {now:%Y-%m-%d %H:%M} UTC"
    )
    phase = "pre-season" if not started else "in-season"
    deadline_line = ""
    if deadline is not None:
        gw_id, when = deadline
        days = (when - now).days
        deadline_line = f"Next deadline: **GW{gw_id} {when:%a %d %b %H:%M} UTC** ({days}d away)."

    index_lines = [
        f"# Weekly Team Report — week {week_label}",
        "",
        f"*Generated from {stamp} — {phase}. {deadline_line}*",
        "",
        (
            "*FPL-API-derived sections are mechanical; other competitions, pre-season"
            " friendlies/transfers, press-conference notes and the rotation outlook are"
            " enriched by the /fpl-team-week-report skill.*"
        ),
        "",
    ]
    if started:
        index_lines += [
            "| Team | PL games last 7d | PL games next 14d | Flagged | Movers |",
            "|---|---|---|---|---|",
        ]
    else:
        index_lines += [
            "| Team | GW1 fixture | Opening 5 avg FDR | Flagged | Movers |",
            "|---|---|---|---|---|",
        ]

    for team_id in sorted(teams, key=lambda t: teams[t]["name"]):
        team = teams[team_id]
        lines = [
            f"# {team['name']} — week {week_label}",
            "",
            f"*{phase} · generated from {stamp}*",
            "",
        ]

        played, window, future = [], [], []
        for fx in fixtures:
            if team_id not in (fx["team_h"], fx["team_a"]):
                continue
            ko = _kickoff(fx)
            if ko is None:
                continue
            if fx.get("finished") and now - timedelta(days=LOOKBACK_DAYS) <= ko <= now:
                played.append(fx)
            elif not fx.get("finished") and ko >= now:
                future.append(fx)
                if ko <= now + timedelta(days=LOOKAHEAD_DAYS):
                    window.append(fx)
        future.sort(key=lambda f: f["kickoff_time"])

        lines.append(f"## Premier League — last {LOOKBACK_DAYS} days")
        if played:
            for fx in sorted(played, key=lambda f: f["kickoff_time"]):
                home, away = teams[fx["team_h"]], teams[fx["team_a"]]
                lines.append(
                    f"- {_kickoff(fx):%a %d %b}: {home['name']} {fx['team_h_score']}"
                    f"–{fx['team_a_score']} {away['name']}"
                )
        elif not started:
            lines.append(
                "- season not started — no PL matches yet. Friendlies go in the"
                " Pre-season section below."
            )
        else:
            lines.append("- no PL matches in the window")

        if window:
            shown = sorted(window, key=lambda f: f["kickoff_time"])
            heading = f"## Premier League — next {LOOKAHEAD_DAYS} days"
        elif not started:
            shown = future[:OPENING_RUN_FIXTURES]
            heading = f"## Premier League — opening run (next {len(shown)} scheduled)"
        else:
            shown = future[:OPENING_RUN_FIXTURES]
            heading = (
                f"## Premier League — next {LOOKAHEAD_DAYS} days"
                " (empty window; next scheduled shown)"
            )
        lines += ["", heading]
        if shown:
            for fx in shown:
                lines.append(_fixture_line(fx, team_id, teams))
            fdrs = [
                fx["team_h_difficulty"] if fx["team_h"] == team_id else fx["team_a_difficulty"]
                for fx in shown
            ]
            lines.append(f"- *avg FDR {sum(fdrs) / len(fdrs):.1f} over {len(shown)}*")
        else:
            lines.append("- no PL fixtures scheduled")

        if not started:
            lines += [
                "",
                "## Pre-season (filled by skill)",
                "",
                (
                    "<!-- skill: friendlies played (score, minutes for key assets),"
                    " confirmed transfers in/out, manager change & expected shape,"
                    " 2026/27 European commitment (UCL/UEL/UECL or none)."
                    " Source + date every claim. -->"
                ),
            ]

        lines += ["", "## Other competitions (filled by skill)", ""]
        lines.append(
            "<!-- skill: UCL/UEL/UECL + FA Cup/EFL Cup matches played & scheduled,"
            " minutes distribution, notable rotation -->"
        )

        flagged = [
            p
            for p in players_by_team.get(team_id, [])
            if STATUS_LABELS.get(p.get("status", "a")) or p.get("news")
        ]
        lines += ["", "## Flagged players (FPL API)"]
        if flagged:
            for p in sorted(flagged, key=lambda x: -_pct(x.get("selected_by_percent"))):
                label = STATUS_LABELS.get(p["status"], p["status"])
                chance = p.get("chance_of_playing_next_round")
                chance_txt = f", {chance}% next round" if chance is not None else ""
                news = (p.get("news") or "").strip()
                lines.append(
                    f"- **{p['web_name']}** ({POSITION_BY_ELEMENT_TYPE[p['element_type']]},"
                    f" {p['selected_by_percent']}% owned): {label or 'flag'}{chance_txt}"
                    f"{' — ' + news if news else ''}"
                )
        else:
            lines.append("- none")

        team_movers = movers.get(team_id, [])
        lines += ["", f"## Price & ownership movers ({movers_baseline})"]
        if prior_dir is None:
            lines.append(
                "- no prior snapshot to diff — run `python -m fpl_claude.data.fpl_api"
                " snapshot` daily and this section fills itself in"
            )
        elif team_movers:
            lines += team_movers
        else:
            lines.append("- no price or ownership movement above threshold")

        lines += [
            "",
            "## Injuries & press conference notes (filled by skill)",
            "",
            "<!-- skill: injuries picked up/cleared this week, presser quotes, sources -->",
            "",
            "## FPL takeaways (filled by skill)",
            "",
            "<!-- skill: rotation risk, assets to buy/sell/hold, congestion verdict -->",
            "",
        ]

        slug = slugify(team["name"], taken=used_slugs)
        _write(week_dir / f"{slug}.md", "\n".join(lines))

        if started:
            index_lines.append(
                f"| {team['name']} | {len(played)} | {len(window)} |"
                f" {len(flagged)} | {len(team_movers)} |"
            )
        else:
            opener = next((fx for fx in future if fx.get("event") == 1), None)
            opener_txt = "TBC"
            if opener is not None:
                is_home = opener["team_h"] == team_id
                opp = teams[opener["team_a"] if is_home else opener["team_h"]]
                opener_txt = f"{opp['short_name']} ({'H' if is_home else 'A'})"
            run = future[:OPENING_RUN_FIXTURES]
            fdrs = [
                fx["team_h_difficulty"] if fx["team_h"] == team_id else fx["team_a_difficulty"]
                for fx in run
            ]
            fdr_txt = f"{sum(fdrs) / len(fdrs):.1f}" if fdrs else "—"
            index_lines.append(
                f"| {team['name']} | {opener_txt} | {fdr_txt} |"
                f" {len(flagged)} | {len(team_movers)} |"
            )

    index_lines += [
        "",
        "## Biggest FPL takeaways this week (filled by skill)",
        "",
        "<!-- skill: the 5-8 things that should change decisions -->",
        "",
    ]
    _write(week_dir / "index.md", "\n".join(index_lines))
    return week_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the weekly all-team report skeletons.")
    parser.add_argument(
        "--from-snapshot",
        metavar="YYYY-MM-DD",
        help="build point-in-time from db/raw/<date>/ instead of the live API",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help=f"root directory for the week folder (default: {REPORTS_DIR})",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help=f"snapshot root for --from-snapshot and the movers baseline (default: {RAW_DIR})",
    )
    args = parser.parse_args(argv)
    week_dir = build_reports(
        from_snapshot=args.from_snapshot, out_dir=args.out_dir, raw_dir=args.raw_dir
    )
    print(f"reports written: {week_dir}")


if __name__ == "__main__":
    main()

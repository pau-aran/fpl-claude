"""Weekly all-team report builder.

Produces one markdown skeleton per PL team for the current ISO week under
reports/weekly/{YYYY-WW}/, pre-filled with everything derivable from FPL API data:

  - PL results in the last 7 days (score, home/away)
  - PL fixtures in the next 14 days with difficulty (congestion count)
  - flagged players: status, news text, chance of playing
  - biggest weekly price/ownership movers

The /fpl-team-week-report skill then enriches each skeleton via web/X search with:
  - non-PL matches played (UCL/UEL/UECL, FA Cup, EFL Cup) and minutes distribution
  - injuries picked up/cleared beyond FPL flags, press-conference notes
  - rotation-risk implications for FPL assets

CLI:  python -m fpl_claude.reports.team_week [--from-snapshot YYYY-MM-DD]
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
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


def _load(from_snapshot: str | None) -> tuple[dict, list[dict]]:
    if from_snapshot:
        day_dir = RAW_DIR / from_snapshot
        bootstrap = json.loads((day_dir / "bootstrap.json").read_text())
        fixtures = json.loads((day_dir / "fixtures.json").read_text())
        return bootstrap, fixtures
    return get_bootstrap(), get_fixtures()


def _kickoff(fixture: dict) -> datetime | None:
    ko = fixture.get("kickoff_time")
    if not ko:
        return None
    return datetime.fromisoformat(ko.replace("Z", "+00:00"))


def build_reports(from_snapshot: str | None = None, out_dir: Path | None = None) -> Path:
    bootstrap, fixtures = _load(from_snapshot)
    now = datetime.now(timezone.utc)
    week_dir = (out_dir or REPORTS_DIR) / f"{date.today():%G-%V}"
    week_dir.mkdir(parents=True, exist_ok=True)

    teams = {t["id"]: t for t in bootstrap["teams"]}
    players_by_team: dict[int, list[dict]] = {}
    for p in bootstrap["elements"]:
        players_by_team.setdefault(p["team"], []).append(p)

    index_lines = [
        f"# Weekly Team Report — week {date.today():%G-W%V}",
        "",
        f"*Generated {now:%Y-%m-%d %H:%M} UTC from FPL API data."
        " Non-PL competitions, press-conference notes and rotation outlook are filled"
        " in by the /fpl-team-week-report skill.*",
        "",
        "| Team | PL games last 7d | PL games next 14d | Flagged players |",
        "|---|---|---|---|",
    ]

    for team_id in sorted(teams, key=lambda t: teams[t]["name"]):
        team = teams[team_id]
        lines = [f"# {team['name']} — week {date.today():%G-W%V}", ""]

        played, upcoming = [], []
        for fx in fixtures:
            if team_id not in (fx["team_h"], fx["team_a"]):
                continue
            ko = _kickoff(fx)
            if ko is None:
                continue
            if fx.get("finished") and now - timedelta(days=7) <= ko <= now:
                played.append(fx)
            elif not fx.get("finished") and now <= ko <= now + timedelta(days=14):
                upcoming.append(fx)

        lines.append("## Premier League — last 7 days")
        if played:
            for fx in sorted(played, key=lambda f: f["kickoff_time"]):
                home, away = teams[fx["team_h"]], teams[fx["team_a"]]
                lines.append(
                    f"- {_kickoff(fx):%a %d %b}: {home['name']} {fx['team_h_score']}"
                    f"–{fx['team_a_score']} {away['name']}"
                )
        else:
            lines.append("- no PL matches in the window")

        lines += ["", "## Premier League — next 14 days"]
        for fx in sorted(upcoming, key=lambda f: f["kickoff_time"]):
            is_home = fx["team_h"] == team_id
            opponent = teams[fx["team_a"] if is_home else fx["team_h"]]
            difficulty = fx["team_h_difficulty"] if is_home else fx["team_a_difficulty"]
            venue = "H" if is_home else "A"
            lines.append(
                f"- {_kickoff(fx):%a %d %b}: {opponent['name']} ({venue}, FDR {difficulty})"
            )
        if not upcoming:
            lines.append("- no PL matches in the window")

        lines += ["", "## Other competitions (filled by skill)", ""]
        lines.append("<!-- skill: UCL/UEL/UECL + FA Cup/EFL Cup matches played & scheduled,"
                     " minutes distribution, notable rotation -->")

        flagged = [
            p for p in players_by_team.get(team_id, [])
            if STATUS_LABELS.get(p.get("status", "a")) or p.get("news")
        ]
        lines += ["", "## Flagged players (FPL API)"]
        if flagged:
            for p in sorted(flagged, key=lambda x: -float(x.get("selected_by_percent") or 0)):
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

        slug = team["name"].lower().replace(" ", "-").replace("'", "")
        (week_dir / f"{slug}.md").write_text("\n".join(lines))
        index_lines.append(
            f"| {team['name']} | {len(played)} | {len(upcoming)} | {len(flagged)} |"
        )

    (week_dir / "index.md").write_text("\n".join(index_lines) + "\n")
    return week_dir


if __name__ == "__main__":
    snapshot_arg = None
    if "--from-snapshot" in sys.argv:
        snapshot_arg = sys.argv[sys.argv.index("--from-snapshot") + 1]
    print(f"reports written: {build_reports(snapshot_arg)}")

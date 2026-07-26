"""Read-only client for the public FPL API.

No authentication, no account access — public endpoints only (owner directive:
manual submission, no FPL account connection).

Endpoints:
  bootstrap-static/          players, teams, events (gameweeks), prices, ownership
  fixtures/                  all PL fixtures with difficulty ratings
  element-summary/{id}/      per-player history + upcoming
  event/{gw}/live/           live/final per-player stats for a gameweek

CLI:  python -m fpl_claude.data.fpl_api snapshot
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from ..console import enable_utf8_output

BASE = "https://fantasy.premierleague.com/api"
USER_AGENT = "fpl-claude/0.1 (research; contact: repo owner)"
RATE_LIMIT_SECONDS = 1.0

# db/ lives at the fpl-claude project root (three levels up from this file's package dir)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "db" / "raw"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_call = 0.0


def _get(path: str) -> Any:
    """GET a JSON endpoint with basic politeness rate limiting and retries."""
    global _last_call
    wait = RATE_LIMIT_SECONDS - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(4):
        try:
            resp = _session.get(f"{BASE}/{path.strip('/')}/", timeout=30)
            _last_call = time.monotonic()
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def get_bootstrap() -> dict:
    """Players, teams, gameweeks, prices, ownership — the core dataset."""
    return _get("bootstrap-static")


def get_fixtures() -> list[dict]:
    """All PL fixtures for the season, with team difficulty ratings."""
    return _get("fixtures")


def get_element_summary(player_id: int) -> dict:
    """Per-player: this season's per-match history, past seasons, upcoming fixtures."""
    return _get(f"element-summary/{player_id}")


def get_event_live(gameweek: int) -> dict:
    """Per-player stats for a gameweek (live during matches, final after)."""
    return _get(f"event/{gameweek}/live")


def current_gameweek(bootstrap: dict | None = None) -> int | None:
    """The current GW id, or None pre-season (no event marked current)."""
    bs = bootstrap or get_bootstrap()
    for event in bs["events"]:
        if event.get("is_current"):
            return event["id"]
    return None


def next_deadline(bootstrap: dict | None = None) -> tuple[int, datetime] | None:
    """(gameweek id, deadline as aware UTC datetime) for the next unfinished GW."""
    bs = bootstrap or get_bootstrap()
    now = datetime.now(timezone.utc)
    for event in bs["events"]:
        deadline = datetime.fromisoformat(event["deadline_time"].replace("Z", "+00:00"))
        if deadline > now:
            return event["id"], deadline
    return None


def snapshot(snapshot_dir: Path | None = None) -> Path:
    """Append-only snapshot of bootstrap + fixtures to db/raw/YYYY-MM-DD/.

    Never overwrites an existing day's snapshot content silently: re-running on the
    same day rewrites that day's files (latest state for the day), but past days are
    untouched — history is reconstructable for point-in-time backtesting.
    """
    day_dir = (snapshot_dir or RAW_DIR) / date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "bootstrap.json": get_bootstrap(),
        "fixtures.json": get_fixtures(),
    }
    for filename, payload in payloads.items():
        (day_dir / filename).write_text(json.dumps(payload, separators=(",", ":")))
    meta = {"fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    (day_dir / "meta.json").write_text(json.dumps(meta))
    return day_dir


def main() -> None:
    enable_utf8_output()
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        path = snapshot()
        print(f"snapshot written: {path}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

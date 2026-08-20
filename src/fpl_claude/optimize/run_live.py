"""CLI runner for the LIVE deadline: projections CSV -> optimizer -> decision dump.

The live twin of `backtest/run.py --propose`: it drives `optimize()` on a real
`db/projections/*.csv` and prints a squad the owner can type into the FPL app,
plus the sanity guards the backtest reviews proved we need. It writes NOTHING
except the optional `--json` dump — models propose, the manager disposes
(CLAUDE.md rule 4), and the decision memo quotes the dump's exact numbers
instead of re-deriving them.

Two modes:
  initial build   no --squad: the GW1 / wildcard case, a 15 within the budget.
                  `--max-spend` caps spend BELOW the rules budget: the last
                  million buys very little, and the unspent remainder banks as
                  an option on the next few deadlines.
  transfer mode   --squad PATH: buys/sells priced through Ruleset.sell_price(),
                  hits charged past the free transfers, and the MARGINAL hit
                  gate applied (a hit must beat the best hit-free solve by
                  policies.hit_ev_threshold PER hit, with the -4 already
                  charged — package deltas smuggle sub-threshold hits).

Squad-state JSON (`--squad`), all money in API tenths (£14.3m -> 143):

    {
      "as_of_gw": 5,                 # informational
      "bank": 8,
      "free_transfers": 2,
      "players": [                   # 15 entries; "name" is a comment, unused
        {"id": 427, "buy_cost": 143, "name": "Haaland"},
        ...
      ]
    }

  `"buy_costs": {"427": 143, ...}` is accepted in place of `players` (same shape
  as the backtest's state.json), so a backtest state file can be replayed live.

Manager overlay flags mirror the backtest's `--decision` JSON, but take NAMES or
ids (`--lock Haaland,427`): at a deadline nobody wants to look up integers.
Names are matched case- and accent-insensitively against `web_name` (so
`Gyokeres` finds `Gyökeres`); qualify with `@` when a surname is shared
(`Pedro@Chelsea`). An ambiguous token is a hard error listing the candidates.

Sanity guards printed every run (all from reports/backtest/2025-26/knowledge.md):
  * 3-per-club usage — over-concentration must be visible before it bites;
  * bench "hairs" — every legal XI<->bench swap inside 0.2 xPts. A 0.14 hair
    stranded 8 points at GW22; the manager sees each close call and decides
    whether to pull `--force-start`;
  * minutes blindness — selected players on `neutral` minutes confidence or
    `low_sample` rates. At a season open that is most new signings and every
    promoted-club player: exactly where the model knows least;
  * FPL flags — selected players carrying an injury/doubt status, read from the
    latest `db/raw/*/bootstrap.json` snapshot (projections carry no flag column).

CLI:
  python -m fpl_claude.optimize.run_live [--projections PATH] [--squad PATH]
      [--lock TOK,...] [--ban TOK,...] [--force-start TOK,...]
      [--force-bench TOK,...] [--captain TOK] [--vice TOK] [--max-transfers N]
      [--max-spend 96.5]
      [--hair-threshold 0.2] [--flags PATH | --no-flags] [--json PATH]
      [--season 2026-27] [--allow-unverified]

`--allow-unverified` runs against a ruleset not yet reconciled with the official
site; the printed header and the JSON dump are then labelled DRY RUN loudly.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..data.fpl_api import PROJECT_ROOT, RAW_DIR
from ..rules.engine import Ruleset
from .milp import (
    CurrentSquad,
    OptimizedSquad,
    RulesetUnverifiedError,
    _immediate_gw_col,
    optimize,
)

PROJECTIONS_DIR = PROJECT_ROOT / "db" / "projections"

# A margin this small between an XI player and a bench player is noise, not a
# decision: the manager must see it and rule, rather than let the solver's
# third decimal pick the starter (backtest GW22, -8).
BENCH_HAIR_THRESHOLD = 0.2

# Confidence levels where the minutes model is running on nothing specific.
BLIND_MINUTES_CONFIDENCE = ("neutral",)


# --------------------------------------------------------------------------
# console robustness (Windows cp1252 vs Gyökeres / Ekitiké / João Pedro)
# --------------------------------------------------------------------------

def _configure_stdout() -> None:
    """Best-effort UTF-8 console; `_out` still guards if this is a no-op."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 — a non-reconfigurable stream is fine, `_out` guards
            with contextlib.suppress(Exception):
                stream.reconfigure(errors="replace")  # type: ignore[union-attr]


def _out(text: str = "") -> None:
    """print() that never dies on a non-ASCII player name."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------

def latest_projections(directory: Path = PROJECTIONS_DIR) -> Path:
    """Newest db/projections/*.csv (filenames are ISO dates, so name-sorted)."""
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise SystemExit(
            f"no projections CSV in {directory} — run "
            "`python -m fpl_claude.models.projections` first, or pass --projections"
        )
    return files[-1]


def load_projections(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    missing = {"id", "web_name", "team", "position", "price", "xpts_horizon"} - set(df.columns)
    if missing:
        raise SystemExit(f"{path} is not a projections table (missing {sorted(missing)})")
    df["id"] = df["id"].astype(int)
    return df.drop_duplicates(subset="id").reset_index(drop=True)


def latest_bootstrap(raw_dir: Path = RAW_DIR) -> Path | None:
    """Newest db/raw/YYYY-MM-DD/bootstrap.json, or None if never snapshotted."""
    files = sorted(raw_dir.glob("*/bootstrap.json"))
    return files[-1] if files else None


def load_flags(path: Path | None) -> dict[int, dict[str, Any]]:
    """player id -> {status, chance, news} from an FPL bootstrap snapshot.

    Projections carry no availability column, so the flag guard reads the raw
    snapshot. 'a' is available; anything else (i/d/s/u/n) is a flag.
    """
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(p["id"]): {
            "status": p.get("status", "a"),
            "chance": p.get("chance_of_playing_next_round"),
            "news": (p.get("news") or "").strip(),
        }
        for p in raw.get("elements", [])
    }


def is_flagged(flag: dict[str, Any] | None) -> bool:
    """True for an injury/doubt flag. Unknown availability is NOT a flag — the
    guard says so separately rather than crying wolf on every player."""
    if not flag:
        return False
    chance = flag.get("chance")
    return (flag.get("status") or "a") != "a" or (chance is not None and chance < 100)


def load_squad_state(path: Path) -> tuple[CurrentSquad, dict[str, Any]]:
    """Parse the squad-state JSON documented in the module docstring."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "players" in raw:
        buy_costs = {int(p["id"]): int(p["buy_cost"]) for p in raw["players"]}
    elif "buy_costs" in raw:
        buy_costs = {int(k): int(v) for k, v in raw["buy_costs"].items()}
    else:
        raise SystemExit(f"{path}: squad state needs a 'players' list or a 'buy_costs' map")
    cheap = {pid: cost for pid, cost in buy_costs.items() if cost < 30}
    if cheap:
        raise SystemExit(
            f"{path}: buy_cost is in API tenths (£4.5m -> 45); these look like £m: {cheap}"
        )
    current = CurrentSquad(
        buy_costs=buy_costs,
        bank=int(raw.get("bank", 0)),
        free_transfers=int(raw.get("free_transfers", 1)),
    )
    return current, {"as_of_gw": raw.get("as_of_gw")}


# --------------------------------------------------------------------------
# name -> id resolution
# --------------------------------------------------------------------------

def _norm(value: Any) -> str:
    """casefold + strip accents, so 'Gyokeres' matches 'Gyökeres'."""
    text = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def resolve_player(token: str, players: pd.DataFrame) -> int:
    """One id from an id or a (possibly '@team'-qualified) name. Ambiguity errors."""
    token = token.strip()
    if not token:
        raise SystemExit("empty player token")
    if re.fullmatch(r"\d+", token):
        pid = int(token)
        if pid not in set(players["id"]):
            raise SystemExit(f"player id {pid} is not in the projections table")
        return pid

    name, _, team = token.partition("@")
    pool = players
    if team:
        pool = pool[pool["team"].map(_norm).str.contains(_norm(team), regex=False)]
        if pool.empty:
            raise SystemExit(f"no club matches {team!r} (from {token!r})")
    target = _norm(name)
    names = pool["web_name"].map(_norm)
    candidates = pool[names == target]
    if len(candidates) != 1:
        candidates = pool[names.str.contains(re.escape(target), regex=True)]
    if len(candidates) == 1:
        return int(candidates.iloc[0]["id"])
    if candidates.empty:
        raise SystemExit(f"no player matches {token!r}")
    listing = ", ".join(
        f"{row.web_name} ({row.team}, id {row.id})" for row in candidates.itertuples()
    )
    raise SystemExit(
        f"{token!r} is ambiguous — {len(candidates)} matches: {listing}. "
        "Use the id, or qualify with @club."
    )


def resolve_tokens(arg: str | None, players: pd.DataFrame) -> frozenset[int]:
    if not arg:
        return frozenset()
    return frozenset(resolve_player(tok, players) for tok in arg.split(",") if tok.strip())


# --------------------------------------------------------------------------
# solve (+ the marginal hit gate)
# --------------------------------------------------------------------------

def solve(
    projections: pd.DataFrame,
    rules: Ruleset,
    current: CurrentSquad | None,
    *,
    lock: frozenset[int] = frozenset(),
    ban: frozenset[int] = frozenset(),
    force_start: frozenset[int] = frozenset(),
    force_bench: frozenset[int] = frozenset(),
    max_transfers: int | None = None,
    max_extra_transfers: int = 1,
    allow_unverified: bool = False,
    budget: int | None = None,
) -> tuple[OptimizedSquad, dict[str, Any]]:
    """Optimizer proposes; the hit policy disposes. Returns (squad, audit).

    Deliberately duplicated from the backtest's `decide_transfers` (the live path
    must not import the backtest package): hits are gated on their MARGINAL NET
    value — the hit solution must beat the best hit-free solution by
    `policies.hit_ev_threshold` PER hit with the -4 already charged, because a
    package delta lets a marginal hit ride in on a big free move.
    """
    kwargs = {
        "rules": rules, "lock": lock, "ban": ban, "force_start": force_start,
        "force_bench": force_bench, "allow_unverified": allow_unverified,
        "budget": budget,
    }
    if current is None:
        return optimize(projections, current=None, **kwargs), {
            "hit_gate": "n/a (initial build)", "hit_marginal": None, "allowance": None,
        }

    allowance = current.free_transfers + max_extra_transfers
    if max_transfers is not None:
        allowance = min(allowance, max_transfers)
    result = optimize(projections, current=current, max_transfers=allowance, **kwargs)
    audit: dict[str, Any] = {
        "hit_gate": "n/a (no hit taken)", "hit_marginal": None, "allowance": allowance,
    }
    if result.hits > 0:
        free = optimize(
            projections, current=current,
            max_transfers=min(current.free_transfers, allowance), **kwargs,
        )
        threshold = float(rules.policy("hit_ev_threshold"))
        marginal = round(result.objective - free.objective, 2)  # already net of -4
        audit["hit_marginal"] = marginal
        if marginal < threshold * result.hits:
            audit["hit_gate"] = f"rejected: net {marginal} < {threshold}/hit"
            result = free
        else:
            audit["hit_gate"] = f"kept: net {marginal} >= {threshold}/hit"
    return result, audit


def apply_captaincy(squad: OptimizedSquad, captain: int | None, vice: int | None) -> OptimizedSquad:
    """Manager armband override — only within the solver's XI, kept distinct."""
    new_c = captain if captain in squad.xi else squad.captain
    new_v = vice if vice in squad.xi else squad.vice
    if new_v == new_c:
        new_v = squad.captain if squad.captain != new_c else squad.vice
    if new_c == squad.captain and new_v == squad.vice:
        return squad
    return OptimizedSquad(**{**squad.__dict__, "captain": new_c, "vice": new_v})


# --------------------------------------------------------------------------
# sanity guards
# --------------------------------------------------------------------------

def club_usage(rows: pd.DataFrame, max_per_club: int) -> list[dict[str, Any]]:
    counts = Counter(rows["team"])
    return [
        {"team": team, "count": n, "at_cap": n >= max_per_club}
        for team, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _swap_legal(
    out_pos: str, in_pos: str, counts: Counter, minimums: dict[str, int], maxima: dict[str, int]
) -> bool:
    if out_pos == in_pos:
        return True
    if "GKP" in (out_pos, in_pos):
        return False  # exactly one keeper starts: GKP only ever swaps with GKP
    return counts[out_pos] - 1 >= minimums[out_pos] and counts[in_pos] + 1 <= maxima[in_pos]


def bench_hairs(
    squad: OptimizedSquad,
    score: dict[int, float],
    pos: dict[int, str],
    rules: Ruleset,
    fit: dict[int, bool],
    threshold: float = BENCH_HAIR_THRESHOLD,
) -> list[dict[str, Any]]:
    """Every legal XI<->bench swap whose xPts margin is under `threshold`.

    Only pairs where BOTH players are fit: promoting a flagged bench player is
    not the call this guard is about (that one is the flag guard's). A negative
    margin means a force_start/force_bench overlay is costing xPts — shown too,
    so the overlay's price is explicit.
    """
    lineup = rules.raw["lineup"]
    shape = rules.squad_shape()
    minimums = {
        "GKP": int(lineup["min_goalkeepers"]), "DEF": int(lineup["min_defenders"]),
        "MID": int(lineup["min_midfielders"]), "FWD": int(lineup["min_forwards"]),
    }
    maxima = {
        "GKP": int(lineup["min_goalkeepers"]),
        "DEF": int(lineup.get("max_defenders", shape["DEF"])),
        "MID": int(lineup.get("max_midfielders", shape["MID"])),
        "FWD": int(lineup.get("max_forwards", shape["FWD"])),
    }
    counts = Counter(pos[i] for i in squad.xi)
    hairs = []
    for bench_id in squad.bench:
        if not fit.get(bench_id, True):
            continue
        for xi_id in squad.xi:
            if not fit.get(xi_id, True):
                continue
            if not _swap_legal(pos[xi_id], pos[bench_id], counts, minimums, maxima):
                continue
            margin = round(score[xi_id] - score[bench_id], 3)
            if margin < threshold:
                hairs.append({
                    "xi_id": xi_id, "bench_id": bench_id, "margin": margin,
                    "xi_score": round(score[xi_id], 2),
                    "bench_score": round(score[bench_id], 2),
                    "bench_slot": squad.bench.index(bench_id) + 1,
                })
    return sorted(hairs, key=lambda h: h["margin"])


def minutes_risk(rows: pd.DataFrame) -> list[dict[str, Any]]:
    """Selected players the minutes/rates models are blind on."""
    risky = []
    for row in rows.itertuples():
        confidence = str(getattr(row, "minutes_confidence", "") or "")
        low_sample = bool(getattr(row, "low_sample", False))
        if confidence in BLIND_MINUTES_CONFIDENCE or low_sample:
            reasons = []
            if confidence in BLIND_MINUTES_CONFIDENCE:
                reasons.append(f"minutes_confidence={confidence}")
            if low_sample:
                reasons.append("low_sample rates")
            risky.append({
                "id": int(row.id), "web_name": row.web_name, "team": row.team,
                "reasons": reasons,
            })
    return risky


def flagged_players(rows: pd.DataFrame, flags: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows.itertuples():
        flag = flags.get(int(row.id))
        if is_flagged(flag):
            out.append({
                "id": int(row.id), "web_name": row.web_name, "team": row.team,
                "status": flag["status"], "chance": flag["chance"], "news": flag["news"],
            })
    return out


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _role(squad: OptimizedSquad, pid: int) -> str:
    if pid == squad.captain:
        return "C"
    if pid == squad.vice:
        return "V"
    if pid in squad.xi:
        return "XI"
    if pid in squad.bench:
        return f"B{squad.bench.index(pid) + 1}"
    return "OUT"  # a sold player, priced from the pool for the transfer table


def _num(value: Any) -> float | None:
    """float or None — NaN would serialise as invalid JSON."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def build_decision(
    squad: OptimizedSquad,
    projections: pd.DataFrame,
    rules: Ruleset,
    *,
    current: CurrentSquad | None,
    audit: dict[str, Any],
    overlay: dict[str, list[int]],
    flags: dict[int, dict[str, Any]],
    xi_col: str,
    score_col: str,
    sources: dict[str, Any],
    dry_run: bool,
    hair_threshold: float,
    spend_cap: int | None = None,
) -> dict[str, Any]:
    """The full decision as plain data — printed, and dumped by --json so the
    memo quotes exact numbers instead of re-deriving them."""
    by_id = projections.set_index("id")
    rows = by_id.loc[squad.squad].reset_index()  # keeps `id` as a column for the guards
    pos = {i: str(by_id.loc[i, "position"]) for i in squad.squad}
    xi_score = {i: float(by_id.loc[i, xi_col]) for i in squad.squad}
    fit = {i: not is_flagged(flags.get(i)) for i in squad.squad}
    price_tenths = {i: round(float(by_id.loc[i, "price"]) * 10) for i in by_id.index}

    def player(pid: int) -> dict[str, Any]:
        row = by_id.loc[pid]
        flag = flags.get(pid) or {}
        return {
            "id": int(pid),
            "web_name": str(row["web_name"]),
            "team": str(row["team"]),
            "position": str(row["position"]),
            "price": float(row["price"]),
            "role": _role(squad, pid),
            "xpts_gw": round(float(row[xi_col]), 2),
            "xpts_horizon": round(float(row[score_col]), 2),
            "ownership_pct": _num(row.get("ownership_pct")),
            "minutes_confidence": str(row.get("minutes_confidence", "")),
            "low_sample": bool(row.get("low_sample", False)),
            "is_pen_taker": bool(row.get("is_pen_taker", False)),
            "status": flag.get("status"),
            "chance_of_playing": flag.get("chance"),
            "news": flag.get("news", ""),
        }

    squad_value = sum(price_tenths[i] for i in squad.squad)
    if current is None:
        budget = round(float(rules.raw["budget"]["initial"]) * 10)
        spend = squad.cost
        # The bank is what the RULES budget leaves, never what a self-imposed
        # spend cap leaves: capping spend does not burn the difference, it banks it.
        bank = budget - spend
    else:
        budget = None
        spend = squad.cost  # transfer mode: outlay on the buys only
        proceeds = sum(
            rules.sell_price(current.buy_costs[i], price_tenths[i])
            for i in squad.transfers_out
        )
        bank = current.bank + proceeds - spend

    transfers = None
    if current is not None:
        transfers = {
            "in": [player(i) for i in squad.transfers_in],
            "out": [
                {**player(i), "sell_price": rules.sell_price(
                    current.buy_costs[i], price_tenths[i]) / 10.0}
                for i in squad.transfers_out
            ],
            "count": len(squad.transfers_in),
            "hits": squad.hits,
            "hit_points": -4 * squad.hits,
            "ev_delta": squad.ev_delta,
            "free_transfers_available": current.free_transfers,
            **audit,
        }

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "initial-build" if current is None else "transfer",
        "dry_run": dry_run,
        "dry_run_reason": (
            "ruleset not verified against the official site (--allow-unverified)"
            if dry_run else None
        ),
        "season": rules.season,
        "ruleset_verified": rules.is_verified(),
        "unverified_sections": rules.unverified_sections(),
        "sources": sources,
        "score_col": score_col,
        "xi_score_col": xi_col,
        "objective": squad.objective,
        "squad": [player(i) for i in squad.squad],
        "xi": [int(i) for i in squad.xi],
        "bench_order": [int(i) for i in squad.bench],
        "captain": player(squad.captain),
        "vice": player(squad.vice),
        "money": {
            "squad_value_m": round(squad_value / 10, 1),
            "spend_m": round(spend / 10, 1),
            "bank_m": round(bank / 10, 1),
            "budget_m": round(budget / 10, 1) if budget is not None else None,
            "spend_cap_m": round(spend_cap / 10, 1) if spend_cap is not None else None,
        },
        "predicted_xi_xpts": round(
            sum(xi_score[i] for i in squad.xi) + xi_score[squad.captain], 2
        ),
        "transfers": transfers,
        "overlay": overlay,
        "guards": {
            "max_per_club": int(rules.raw["squad"]["max_per_club"]),
            "club_usage": club_usage(rows, int(rules.raw["squad"]["max_per_club"])),
            "bench_hair_threshold": hair_threshold,
            "bench_hairs": bench_hairs(
                squad, xi_score, pos, rules, fit, threshold=hair_threshold
            ),
            "minutes_risk": minutes_risk(rows),
            "flagged": flagged_players(rows, flags),
            "flags_available": bool(flags),
        },
    }


def _table(players: list[dict[str, Any]], xi_col: str) -> str:
    frame = pd.DataFrame([
        {
            "role": p["role"], "name": p["web_name"], "club": p["team"],
            "pos": p["position"], "£m": p["price"], xi_col: p["xpts_gw"],
            "horizon": p["xpts_horizon"], "own%": p["ownership_pct"],
            "mins": p["minutes_confidence"],
            "!": ("FLAG" if is_flagged(
                {"status": p["status"], "chance": p["chance_of_playing"]}) else ""),
        }
        for p in players
    ])
    return frame.to_string(index=False)


def print_decision(decision: dict[str, Any]) -> None:
    d = decision
    _out("=" * 78)
    if d["dry_run"]:
        _out("*** DRY RUN — RULES UNVERIFIED — NOT A SUBMITTABLE DECISION ***")
        _out(f"*** {d['dry_run_reason']}; unverified: {d['unverified_sections']} ***")
    mode = "INITIAL BUILD (GW1 / wildcard)" if d["mode"] == "initial-build" else "TRANSFER MODE"
    _out(f"fpl-claude live optimizer — {mode} — season {d['season']}")
    _out(f"projections: {d['sources']['projections']}")
    _out(f"flags:       {d['sources']['flags'] or 'NONE (no bootstrap snapshot — flag guard off)'}")
    _out(f"squad bought on {d['score_col']}; XI/captain/bench ordered on {d['xi_score_col']}")
    _out("=" * 78)

    xi = [p for p in d["squad"] if p["id"] in d["xi"]]
    bench = [p for p in d["squad"] if p["id"] not in d["xi"]]
    bench.sort(key=lambda p: d["bench_order"].index(p["id"]))
    _out("\n--- STARTING XI ---")
    _out(_table(xi, d["xi_score_col"]))
    _out("\n--- BENCH (autosub order) ---")
    _out(_table(bench, d["xi_score_col"]))

    money = d["money"]
    _out(
        f"\ncaptain: {d['captain']['web_name']} ({d['captain']['team']}) | "
        f"vice: {d['vice']['web_name']} ({d['vice']['team']})"
    )
    budget = f" of £{money['budget_m']}m" if money["budget_m"] is not None else ""
    cap = (
        f" (spend capped at £{money['spend_cap_m']}m)"
        if money.get("spend_cap_m") is not None
        else ""
    )
    _out(
        f"squad value £{money['squad_value_m']}m | spend £{money['spend_m']}m{budget}{cap} | "
        f"bank £{money['bank_m']}m | predicted XI xPts {d['predicted_xi_xpts']} "
        f"(captain doubled) | objective {d['objective']}"
    )

    t = d["transfers"]
    if t is not None:
        _out("\n--- TRANSFERS ---")
        if not t["in"]:
            _out("roll: no move clears the bar")
        for out_p, in_p in zip(t["out"], t["in"]):
            _out(
                f"OUT {out_p['web_name']} ({out_p['team']}, sell £{out_p['sell_price']}m)"
                f"  ->  IN {in_p['web_name']} ({in_p['team']}, £{in_p['price']}m)"
            )
        _out(
            f"transfers {t['count']} | free {t['free_transfers_available']} | "
            f"hits {t['hits']} ({t['hit_points']} pts) | ev_delta {t['ev_delta']} | "
            f"gate: {t['hit_gate']}"
        )

    g = d["guards"]
    _out("\n--- SANITY GUARDS ---")
    usage = "  ".join(
        f"{c['team']}:{c['count']}{'*' if c['at_cap'] else ''}" for c in g["club_usage"]
    )
    _out(f"club usage (cap {g['max_per_club']}, * = at cap): {usage}")

    if g["bench_hairs"]:
        _out(
            f"\nbench-order HAIRS (< {g['bench_hair_threshold']} xPts between fit players — "
            "the manager rules on each; --force-start to pull one):"
        )
        for h in g["bench_hairs"]:
            names = {p["id"]: p["web_name"] for p in d["squad"]}
            _out(
                f"  {names[h['xi_id']]} (XI, {h['xi_score']}) vs "
                f"{names[h['bench_id']]} (B{h['bench_slot']}, {h['bench_score']}) "
                f"-> margin {h['margin']:+.3f}"
            )
    else:
        _out(f"bench-order hairs: none under {g['bench_hair_threshold']} xPts")

    if g["minutes_risk"]:
        _out(
            f"\nMINUTES BLIND SPOTS ({len(g['minutes_risk'])}/{len(d['squad'])} selected — "
            "model knows least here; check the news sweep):"
        )
        for r in g["minutes_risk"]:
            _out(f"  {r['web_name']} ({r['team']}): {', '.join(r['reasons'])}")
    else:
        _out("minutes blind spots: none")

    if not g["flags_available"]:
        _out("\nFPL FLAGS: no bootstrap snapshot loaded — availability UNCHECKED")
    elif g["flagged"]:
        _out("\nFPL FLAGS on selected players (written reasoning required — CLAUDE.md rule 5):")
        for f in g["flagged"]:
            chance = "?" if f["chance"] is None else f"{f['chance']}%"
            _out(f"  {f['web_name']} ({f['team']}): status={f['status']} chance={chance} "
                 f"— {f['news'] or 'no news text'}")
    else:
        _out("\nFPL flags on selected players: none")

    o = d["overlay"]
    if any(o.values()):
        _out(f"\nmanager overlay applied: {json.dumps(o)}")
    _out("\nThis is a CANDIDATE, not an order (CLAUDE.md rule 4).")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m fpl_claude.optimize.run_live",
        description="Live FPL squad / transfer optimizer (see module docstring).",
    )
    p.add_argument("--projections", default=None,
                   help="projections CSV (default: newest in db/projections/)")
    p.add_argument("--squad", default=None,
                   help="squad-state JSON -> transfer mode (default: initial build)")
    p.add_argument("--lock", default=None, help="ids/names to force INTO the squad")
    p.add_argument("--ban", default=None, help="ids/names to refuse to own")
    p.add_argument("--force-start", default=None, help="owned ids/names to force into the XI")
    p.add_argument("--force-bench", default=None, help="owned ids/names to force onto the bench")
    p.add_argument("--captain", default=None, help="armband override (id or name, must be in XI)")
    p.add_argument("--vice", default=None, help="vice override (id or name, must be in XI)")
    p.add_argument("--max-transfers", type=int, default=None,
                   help="hard cap on transfers (0 = roll)")
    p.add_argument("--max-extra-transfers", type=int, default=1,
                   help="hits the solver may consider beyond free transfers (default 1)")
    p.add_argument("--max-spend", type=float, default=None,
                   help="initial build only: cap squad SPEND at this many £m "
                        "(<= the rules budget). The unspent remainder banks.")
    p.add_argument("--hair-threshold", type=float, default=BENCH_HAIR_THRESHOLD,
                   help=f"bench-hair margin in xPts (default {BENCH_HAIR_THRESHOLD})")
    p.add_argument("--flags", default=None,
                   help="bootstrap.json for the flag guard (default: newest db/raw/*/)")
    p.add_argument("--no-flags", action="store_true", help="skip the FPL flag guard")
    p.add_argument("--json", dest="json_path", default=None,
                   help="write the full decision JSON here (memos quote it)")
    p.add_argument("--season", default="2026-27")
    p.add_argument("--allow-unverified", action="store_true",
                   help="run against an unverified ruleset; output is labelled DRY RUN")
    return p


def main(argv: list[str] | None = None) -> None:
    _configure_stdout()
    args = build_parser().parse_args(argv)

    rules = Ruleset.load(args.season)
    proj_path = Path(args.projections) if args.projections else latest_projections()
    projections = load_projections(proj_path)

    lock = resolve_tokens(args.lock, projections)
    ban = resolve_tokens(args.ban, projections)
    force_start = resolve_tokens(args.force_start, projections)
    force_bench = resolve_tokens(args.force_bench, projections)
    captain = resolve_player(args.captain, projections) if args.captain else None
    vice = resolve_player(args.vice, projections) if args.vice else None

    current, meta = (None, {})
    if args.squad:
        current, meta = load_squad_state(Path(args.squad))
        missing = set(current.buy_costs) - set(projections["id"])
        if missing:
            raise SystemExit(
                f"owned players absent from {proj_path.name}: {sorted(missing)} "
                "(stale squad file, or a departed player — fix the squad JSON)"
            )

    spend_cap = round(args.max_spend * 10) if args.max_spend is not None else None
    if spend_cap is not None and current is not None:
        raise SystemExit("--max-spend applies to an initial build only (no --squad)")

    flags_path = None
    if not args.no_flags:
        flags_path = Path(args.flags) if args.flags else latest_bootstrap()
    flags = load_flags(flags_path)

    try:
        squad, audit = solve(
            projections, rules, current,
            lock=lock, ban=ban, force_start=force_start, force_bench=force_bench,
            max_transfers=args.max_transfers,
            max_extra_transfers=args.max_extra_transfers,
            allow_unverified=args.allow_unverified,
            budget=spend_cap,
        )
    except RulesetUnverifiedError as exc:
        raise SystemExit(f"{exc}\n\nRe-run with --allow-unverified for a labelled dry run.")

    squad = apply_captaincy(squad, captain, vice)

    xi_col = _immediate_gw_col(projections.columns) or "xpts_horizon"
    decision = build_decision(
        squad, projections, rules,
        current=current, audit=audit,
        overlay={
            "lock": sorted(lock), "ban": sorted(ban),
            "force_start": sorted(force_start), "force_bench": sorted(force_bench),
            "captain": captain, "vice": vice,
            "max_transfers": args.max_transfers,
        },
        flags=flags, xi_col=xi_col, score_col="xpts_horizon",
        sources={
            "projections": str(proj_path),
            "flags": str(flags_path) if flags_path else None,
            "squad_state": str(args.squad) if args.squad else None,
            "as_of_gw": meta.get("as_of_gw"),
        },
        dry_run=args.allow_unverified and not rules.is_verified(),
        hair_threshold=args.hair_threshold,
        spend_cap=spend_cap,
    )

    print_decision(decision)

    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(decision, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        _out(f"\ndecision JSON: {out}")


if __name__ == "__main__":
    main()

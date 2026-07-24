"""CLI runner for one backtest gameweek: project -> decide -> score -> memo.

Designed for the week-by-week evolution loop: state (squad, bank, free
transfers, running totals) persists to JSON between invocations, so pipeline
improvements made after GW n only affect GW n+1 onward — past results stay
what they were, exactly like a real season. Rerunning a completed GW with
changed code would rewrite history; the runner refuses unless --force.

Per GW it writes into --out:
  gw{NN}.md           decision memo (transfers, XI, captain, EV, outcome)
  gw{NN}_players.csv  per-squad-player predicted vs actual
  state.json          rolling squad state (input for the next GW)

Overlays: --overlays JSON {player_id: {start_share, reason}} — hand-written
news replays; merged over the automatic availability proxies (hand wins).

CLI: python -m fpl_claude.backtest.run --data DIR --gw N --out DIR
        [--state PATH] [--overlays PATH] [--season 2025-26] [--force]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


from ..rules.engine import Ruleset
from .data import SeasonStore
from .overlays import availability_overlays, merge
from .simulate import (
    GWResult,
    ManagerDecision,
    SquadState,
    decide_transfers,
    project_gw,
    run_gameweek,
)


def load_state(path: Path) -> SquadState | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return SquadState(
        buy_costs={int(k): int(v) for k, v in raw["buy_costs"].items()},
        bank=int(raw["bank"]),
        free_transfers=int(raw["free_transfers"]),
        points_total=int(raw["points_total"]),
        hits_total=int(raw["hits_total"]),
        chips_used=list(raw.get("chips_used", [])),
    )


def save_state(state: SquadState, path: Path, gw: int) -> None:
    path.write_text(
        json.dumps(
            {
                "last_gw": gw,
                "buy_costs": state.buy_costs,
                "bank": state.bank,
                "free_transfers": state.free_transfers,
                "points_total": state.points_total,
                "hits_total": state.hits_total,
                "chips_used": state.chips_used,
            },
            indent=2,
        )
    )


def load_decision(path: Path | None) -> ManagerDecision | None:
    """Manager decision JSON: {lock: [ids], ban: [ids], captain: id, vice: id,
    max_transfers: int, start: [ids], bench: [ids], reasoning: str} — all
    fields optional. start/bench force an owned player into / out of the XI."""
    if path is None:
        return None
    raw = json.loads(path.read_text())
    return ManagerDecision(
        lock=frozenset(int(i) for i in raw.get("lock", [])),
        ban=frozenset(int(i) for i in raw.get("ban", [])),
        captain=raw.get("captain"),
        vice=raw.get("vice"),
        max_transfers=raw.get("max_transfers"),
        start=frozenset(int(i) for i in raw.get("start", [])),
        bench=frozenset(int(i) for i in raw.get("bench", [])),
        chip=raw.get("chip"),
        reasoning=str(raw.get("reasoning", "")),
    )


def propose(store: SeasonStore, gw: int, rules: Ruleset, state: SquadState,
            overlays: dict | None, decision: ManagerDecision | None) -> None:
    """Print the optimizer proposal + multi-GW fixture context. NO state is
    written: this is the 'models propose' half; the manager call comes after."""
    projections = project_gw(store, gw, rules, overlays=overlays)
    squad, audit = decide_transfers(projections, rules, state, decision=decision)
    by_id = projections.drop_duplicates("id").set_index("id")
    outlook = store.fixture_outlook(gw)

    def nm(pid: int) -> str:
        return str(by_id.loc[pid, "web_name"]) if pid in by_id.index else str(pid)

    print(f"=== GW{gw} PROPOSAL (nothing saved) ===")
    if squad.transfers_in:
        for o, i in zip(squad.transfers_out, squad.transfers_in):
            print(f"transfer: {nm(o)} ({by_id.loc[o, 'team']}) -> {nm(i)} ({by_id.loc[i, 'team']})")
        print(f"hits: {squad.hits} | ev_delta vs roll: {squad.ev_delta} | gate: {audit['hit_gate']}")
    else:
        print("transfers: roll")
    print(f"captain: {nm(squad.captain)} | vice: {nm(squad.vice)}")
    cols = [c for c in (f"xpts_gw{gw}", "xpts_horizon", "price", "exp_minutes_gw") if c in by_id.columns]
    rows = by_id.loc[squad.squad, ["web_name", "team", "position", *cols]]
    rows["fixtures_next"] = rows["team"].map(outlook)
    rows["role"] = ["C" if i == squad.captain else "V" if i == squad.vice
                    else "XI" if i in squad.xi else "bench" for i in rows.index]
    print(rows.to_string())
    print("\nTop 12 by horizon xPts outside squad (with fixture runs):")
    outside = by_id[~by_id.index.isin(squad.squad)].nlargest(12, "xpts_horizon")
    out_rows = outside[["web_name", "team", "position", "price", "xpts_horizon"]].copy()
    out_rows["fixtures_next"] = out_rows["team"].map(outlook)
    print(out_rows.to_string())


def _name(result: GWResult, pid: int) -> str:
    match = result.player_rows[result.player_rows["id"] == pid]
    if len(match):
        return str(match.iloc[0]["web_name"])
    return result.names.get(pid, str(pid))


def write_memo(
    result: GWResult,
    state: SquadState,
    out_dir: Path,
    overlays_used: dict[int, dict] | None,
    decision: ManagerDecision | None = None,
    outlook: dict[str, str] | None = None,
) -> Path:
    r, rows = result, result.player_rows
    lines = [
        f"# Backtest 2025/26 — GW{r.gw} decision memo",
        "",
        f"*Point-in-time replay: models saw only GW1–GW{r.gw - 1} data plus 2024/25 priors.*",
        "",
        "## Decision",
        "",
    ]
    if r.chip:
        _CHIP_LABEL = {
            "wildcard": "WILDCARD", "free_hit": "FREE HIT",
            "bench_boost": "BENCH BOOST", "triple_captain": "TRIPLE CAPTAIN",
        }
        lines.append(f"- **CHIP PLAYED: {_CHIP_LABEL.get(r.chip, r.chip.upper())}**")
    lines += [
        f"- Captain: **{_name(r, r.squad.captain)}** | vice: {_name(r, r.squad.vice)}",
        f"- Bank after moves: £{r.bank / 10:.1f}m | free transfers left for next GW: {r.free_transfers_left}",
    ]
    if r.transfers:
        moves = ", ".join(f"{_name(r, o)} → {_name(r, i)}" for o, i in r.transfers)
        hit_note = f" ({r.hits} hit(s), -{r.hits * 4})" if r.hits else " (free)"
        ev = f", ev_delta {r.squad.ev_delta:+.2f}" if r.squad.ev_delta is not None else ""
        lines.append(f"- Transfers: {moves}{hit_note}{ev}")
    else:
        lines.append("- Transfers: none (initial build)" if r.gw == 1 else "- Transfers: roll")
    if decision is not None and (
        decision.lock or decision.ban or decision.captain or decision.vice
        or decision.max_transfers is not None or decision.reasoning
    ):
        lines += ["", "## Manager overlay (the human call, outside the algorithm)", ""]
        if decision.reasoning:
            lines.append(decision.reasoning.strip())
            lines.append("")
        if decision.lock:
            lines.append("- Locked (refused to sell/insisted on): "
                         + ", ".join(_name(r, i) for i in sorted(decision.lock)))
        if decision.ban:
            lines.append("- Banned (refused to own): "
                         + ", ".join(_name(r, i) for i in sorted(decision.ban)))
        if decision.captain is not None:
            lines.append(f"- Captain override: {_name(r, decision.captain)}")
        if decision.max_transfers is not None:
            lines.append(f"- Transfer cap imposed: {decision.max_transfers}")
    if outlook:
        squad_teams = list(dict.fromkeys(rows["team"]))
        lines += ["", "## Fixture outlook (squad clubs, next 5 GWs)", ""]
        for team in squad_teams:
            lines.append(f"- {team}: {outlook.get(team, '—')}")
    if overlays_used:
        lines += ["", "## Overlays applied (written reasons)", ""]
        for pid, ov in sorted(overlays_used.items()):
            if (rows["id"] == pid).any():  # only list overlays touching our squad pool decision
                lines.append(
                    f"- {_name(r, pid)}: start_share={ov['start_share']} — {ov['reason']}"
                )
    cap_word = {2: "doubled", 3: "tripled"}.get(r.captain_mult, f"x{r.captain_mult}")
    lines += [
        "",
        "## Squad — predicted vs actual",
        "",
        rows[
            ["web_name", "team", "position", "price", "predicted", "actual", "minutes", "role"]
        ].to_markdown(index=False),
        "",
        "## Outcome",
        "",
        f"- Predicted XI points: **{r.predicted_xi_pts}** = base XI {r.base_xi_pts} "
        f"+ captain slot {r.captain_slot_pts} ({cap_word}). Split logged because the "
        f"season residual is a small within-noise base bias plus a mean-unbiased, "
        f"high-variance captain slot — read EV against that "
        f"(reports/backtest/2025-26/calibration.md).",
        f"- Actual GW points (after autosubs & hits): **{r.actual_pts}**",
        f"- Effective captain: {_name(r, r.effective_captain)}",
        "- Autosubs: "
        + (
            ", ".join(f"{_name(r, o)} → {_name(r, i)}" for o, i in r.autosubs)
            if r.autosubs
            else "none"
        ),
        f"- Season total: **{state.points_total}** pts | hits taken: {state.hits_total}",
        "",
    ]
    path = out_dir / f"gw{r.gw:02d}.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="vaastav data root (contains 2025-26/)")
    parser.add_argument("--gw", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--state", default=None, help="state.json path (default: <out>/state.json)")
    parser.add_argument("--overlays", default=None, help="hand-written overlay JSON for this GW")
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--force", action="store_true", help="allow re-running a completed GW")
    parser.add_argument("--decision", default=None,
                        help="manager decision JSON (lock/ban/captain/max_transfers/chip/reasoning)")
    parser.add_argument("--chip", default=None,
                        help="play a chip this GW: wildcard|free_hit|bench_boost|triple_captain "
                             "(overrides the decision JSON's chip)")
    parser.add_argument("--propose", action="store_true",
                        help="print the optimizer proposal + fixture outlook and exit; no writes")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state) if args.state else out_dir / "state.json"

    state = load_state(state_path)
    if state_path.exists():
        last = json.loads(state_path.read_text())["last_gw"]
        if args.gw != last + 1 and not args.force and not args.propose:
            raise SystemExit(
                f"state is at GW{last}; next is GW{last + 1}, not GW{args.gw} "
                "(pass --force to rewrite history deliberately)"
            )
    elif args.gw != 1:
        raise SystemExit("no state.json — the season must start at --gw 1")

    store = SeasonStore(Path(args.data), season=args.season)
    rules = Ruleset.load(args.season)

    hand = None
    if args.overlays:
        hand = {int(k): v for k, v in json.loads(Path(args.overlays).read_text()).items()}
    overlays = merge(availability_overlays(store, args.gw), hand)

    decision = load_decision(Path(args.decision) if args.decision else None)
    if args.chip:
        from dataclasses import replace
        decision = replace(decision or ManagerDecision(), chip=args.chip)

    if args.propose:
        if state is None:
            raise SystemExit("--propose needs an existing state.json (GW2 onward)")
        propose(store, args.gw, rules, state, overlays or None, decision)
        return

    result, state = run_gameweek(
        store, args.gw, rules, state, overlays=overlays or None, decision=decision
    )

    result.player_rows.to_csv(out_dir / f"gw{args.gw:02d}_players.csv", index=False)
    memo = write_memo(result, state, out_dir, overlays, decision,
                      store.fixture_outlook(args.gw))
    save_state(state, state_path, args.gw)

    print(f"GW{args.gw}: predicted {result.predicted_xi_pts} | actual {result.actual_pts} "
          f"| season total {state.points_total} | memo {memo}")


if __name__ == "__main__":
    main()

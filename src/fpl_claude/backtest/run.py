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
from .simulate import GWResult, SquadState, run_gameweek


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
            },
            indent=2,
        )
    )


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
) -> Path:
    r, rows = result, result.player_rows
    lines = [
        f"# Backtest 2025/26 — GW{r.gw} decision memo",
        "",
        f"*Point-in-time replay: models saw only GW1–GW{r.gw - 1} data plus 2024/25 priors.*",
        "",
        "## Decision",
        "",
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
    if overlays_used:
        lines += ["", "## Overlays applied (written reasons)", ""]
        for pid, ov in sorted(overlays_used.items()):
            if (rows["id"] == pid).any():  # only list overlays touching our squad pool decision
                lines.append(
                    f"- {_name(r, pid)}: start_share={ov['start_share']} — {ov['reason']}"
                )
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
        f"- Predicted XI points (incl. captain double): **{r.predicted_xi_pts}**",
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
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state) if args.state else out_dir / "state.json"

    state = load_state(state_path)
    if state_path.exists():
        last = json.loads(state_path.read_text())["last_gw"]
        if args.gw != last + 1 and not args.force:
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

    result, state = run_gameweek(store, args.gw, rules, state, overlays=overlays or None)

    result.player_rows.to_csv(out_dir / f"gw{args.gw:02d}_players.csv", index=False)
    memo = write_memo(result, state, out_dir, overlays)
    save_state(state, state_path, args.gw)

    print(f"GW{args.gw}: predicted {result.predicted_xi_pts} | actual {result.actual_pts} "
          f"| season total {state.points_total} | memo {memo}")


if __name__ == "__main__":
    main()

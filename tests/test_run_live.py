"""Live optimizer CLI tests — synthetic projections, offline, no real CSV needed.

The frame deliberately carries the awkward parts of real data: accented names
(the Windows cp1252 console bug), a duplicated surname (ambiguous resolution),
a stacked club (3-per-club), neutral minutes confidence and low_sample rows.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from fpl_claude.optimize import run_live
from fpl_claude.optimize.milp import CurrentSquad, optimize
from fpl_claude.rules.engine import Ruleset

NAMES = {
    ("T1", "FWD", 0): "Gyökeres",   # accents: must survive printing + CSV round-trip
    ("T2", "FWD", 0): "Ekitiké",
    ("T3", "MID", 0): "Pedro",      # duplicated surname -> ambiguous token
    ("T4", "MID", 0): "Pedro",
}


def _pool() -> pd.DataFrame:
    """6 clubs x (2 GKP, 3 DEF, 3 MID, 2 FWD) = 60 players, feasible under £100m."""
    rows = []
    pid = 0
    for t, team in enumerate(f"T{k}" for k in range(1, 7)):
        for position, count, base_price in (
            ("GKP", 2, 4.0), ("DEF", 3, 4.0), ("MID", 3, 5.0), ("FWD", 2, 5.5),
        ):
            for j in range(count):
                pid += 1
                score = pid / 10.0 + (10.0 if team == "T1" else 0.0)
                rows.append(
                    {
                        "id": pid,
                        "web_name": NAMES.get((team, position, j), f"{team}-{position}{j}"),
                        "team": team,
                        "position": position,
                        "price": base_price + j * 0.5 + t * 0.2,
                        "xpts_horizon": round(score, 2),
                        "xpts_gw1": round(score / 3, 2),
                        "ownership_pct": 5.0,
                        "minutes_confidence": "season" if pid % 7 else "neutral",
                        "low_sample": pid % 11 == 0,
                        "is_pen_taker": False,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def rules() -> Ruleset:
    return Ruleset.load("2026-27")


@pytest.fixture(scope="module")
def pool() -> pd.DataFrame:
    return _pool()


@pytest.fixture
def csv_path(tmp_path_factory, pool) -> str:
    path = tmp_path_factory.mktemp("projections") / "2026-08-19.csv"
    pool.to_csv(path, index=False, encoding="utf-8")
    return str(path)


# --------------------------------------------------------------------------
# initial build
# --------------------------------------------------------------------------

def test_initial_build_respects_budget_quota_and_club_cap(pool, rules, capsys):
    run_live.main(["--projections", _write(pool, "a"), "--allow-unverified"])
    out = capsys.readouterr().out
    assert "INITIAL BUILD" in out
    assert "DRY RUN" not in out  # 2026-27 IS verified: the label must not fire

    squad, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    by_id = pool.set_index("id")
    rows = by_id.loc[squad.squad]
    assert len(squad.squad) == 15 and len(squad.xi) == 11 and len(squad.bench) == 4
    assert rows["position"].value_counts().to_dict() == {"DEF": 5, "MID": 5, "GKP": 2, "FWD": 3}
    assert rows["team"].value_counts().max() <= 3
    assert squad.cost <= int(rules.raw["budget"]["initial"] * 10)


def _write(frame: pd.DataFrame, tag: str) -> str:
    import tempfile
    from pathlib import Path

    path = Path(tempfile.mkdtemp(prefix=f"fplproj-{tag}-")) / "2026-08-19.csv"
    frame.to_csv(path, index=False, encoding="utf-8")
    return str(path)


def test_accented_names_survive_the_pipeline(pool, csv_path, capsys):
    """The cp1252 console bug: printing Gyökeres must not raise, and the JSON
    dump must round-trip the accents."""
    import tempfile
    from pathlib import Path

    dump = Path(tempfile.mkdtemp()) / "decision.json"
    run_live.main([
        "--projections", csv_path, "--allow-unverified",
        "--lock", "Gyokeres",  # unaccented input resolves to the accented name
        "--json", str(dump),
    ])
    capsys.readouterr()
    payload = json.loads(dump.read_text(encoding="utf-8"))
    assert any(p["web_name"] == "Gyökeres" for p in payload["squad"])


# --------------------------------------------------------------------------
# name -> id resolution
# --------------------------------------------------------------------------

def test_resolve_by_id_name_and_accent_folding(pool):
    ekitike = int(pool.loc[pool["web_name"] == "Ekitiké", "id"].iloc[0])
    assert run_live.resolve_player(str(ekitike), pool) == ekitike
    assert run_live.resolve_player("Ekitiké", pool) == ekitike
    assert run_live.resolve_player("ekitike", pool) == ekitike  # accent- and case-folded
    assert run_live.resolve_player("T2-DEF1", pool) == int(
        pool.loc[pool["web_name"] == "T2-DEF1", "id"].iloc[0]
    )


def test_resolve_ambiguous_name_errors_with_candidates(pool):
    with pytest.raises(SystemExit) as exc:
        run_live.resolve_player("Pedro", pool)
    message = str(exc.value)
    assert "ambiguous" in message and "T3" in message and "T4" in message


def test_resolve_ambiguity_broken_by_club_qualifier(pool):
    expected = int(pool.loc[(pool["web_name"] == "Pedro") & (pool["team"] == "T4"), "id"].iloc[0])
    assert run_live.resolve_player("Pedro@T4", pool) == expected


def test_resolve_unknown_token_errors(pool):
    with pytest.raises(SystemExit, match="no player matches"):
        run_live.resolve_player("Nobody", pool)
    with pytest.raises(SystemExit, match="not in the projections"):
        run_live.resolve_player("99999", pool)


def test_resolve_tokens_mixes_ids_and_names(pool):
    ids = run_live.resolve_tokens("Ekitiké,3", pool)
    assert 3 in ids and len(ids) == 2


# --------------------------------------------------------------------------
# manager overlay
# --------------------------------------------------------------------------

def test_lock_and_ban_are_honoured(pool, rules):
    base, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    outside = next(i for i in pool["id"] if i not in base.squad)
    star = base.squad[0]

    locked, _ = run_live.solve(
        pool, rules, None, lock=frozenset({int(outside)}), allow_unverified=True
    )
    banned, _ = run_live.solve(
        pool, rules, None, ban=frozenset({int(star)}), allow_unverified=True
    )
    assert outside in locked.squad
    assert star not in banned.squad
    assert locked.objective <= base.objective and banned.objective <= base.objective


def test_captain_override_keeps_vice_distinct(pool, rules):
    squad, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    new_captain = squad.vice  # promote the vice: the old captain must become vice
    moved = run_live.apply_captaincy(squad, new_captain, None)
    assert moved.captain == new_captain and moved.vice == squad.captain

    ignored = run_live.apply_captaincy(squad, 99999, None)  # not in the XI -> no-op
    assert ignored.captain == squad.captain


def test_max_transfers_zero_rolls_the_squad(pool, rules):
    current = _own_worst(pool)
    squad, audit = run_live.solve(
        pool, rules, current, max_transfers=0, allow_unverified=True
    )
    assert squad.transfers_in == [] and squad.hits == 0
    assert audit["allowance"] == 0


# --------------------------------------------------------------------------
# transfer mode / squad state JSON
# --------------------------------------------------------------------------

def _own_worst(pool: pd.DataFrame, bank: int = 100) -> CurrentSquad:
    """A legal but deliberately weak 15, so upgrades exist."""
    counts = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    club: dict[str, int] = {}
    ids: list[int] = []
    for _, row in pool.sort_values("xpts_horizon").iterrows():
        if counts.get(row["position"], 0) > 0 and club.get(row["team"], 0) < 3:
            ids.append(int(row["id"]))
            counts[row["position"]] -= 1
            club[row["team"]] = club.get(row["team"], 0) + 1
        if len(ids) == 15:
            break
    prices = pool.set_index("id")["price"]
    return CurrentSquad(
        buy_costs={i: round(float(prices.loc[i]) * 10) for i in ids},
        bank=bank,
        free_transfers=1,
    )


def test_squad_state_json_round_trip(pool, tmp_path):
    current = _own_worst(pool)
    state = {
        "as_of_gw": 5,
        "bank": current.bank,
        "free_transfers": current.free_transfers,
        "players": [{"id": i, "buy_cost": c} for i, c in current.buy_costs.items()],
    }
    path = tmp_path / "squad.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    loaded, meta = run_live.load_squad_state(path)
    assert loaded == current and meta["as_of_gw"] == 5

    # the backtest's buy_costs-map shape is accepted too
    path.write_text(json.dumps({
        "bank": 100, "free_transfers": 1,
        "buy_costs": {str(i): c for i, c in current.buy_costs.items()},
    }), encoding="utf-8")
    assert run_live.load_squad_state(path)[0] == current


def test_squad_state_rejects_pounds_instead_of_tenths(tmp_path):
    path = tmp_path / "squad.json"
    path.write_text(json.dumps({"players": [{"id": 1, "buy_cost": 14.3}]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="tenths"):
        run_live.load_squad_state(path)


def test_transfer_mode_reports_moves_and_gate(pool, rules, tmp_path, capsys):
    current = _own_worst(pool)
    state = {
        "bank": current.bank, "free_transfers": current.free_transfers,
        "players": [{"id": i, "buy_cost": c} for i, c in current.buy_costs.items()],
    }
    squad_path = tmp_path / "squad.json"
    squad_path.write_text(json.dumps(state), encoding="utf-8")
    dump = tmp_path / "decision.json"

    run_live.main([
        "--projections", _write(pool, "transfer"), "--squad", str(squad_path),
        "--allow-unverified", "--json", str(dump),
    ])
    out = capsys.readouterr().out
    assert "TRANSFER MODE" in out and "TRANSFERS" in out

    payload = json.loads(dump.read_text(encoding="utf-8"))
    assert payload["mode"] == "transfer"
    t = payload["transfers"]
    assert len(t["in"]) == len(t["out"]) == t["count"] >= 1
    assert t["ev_delta"] is not None and t["hit_gate"]
    # bank arithmetic: what we started with, plus sales, minus buys.
    assert payload["money"]["bank_m"] == pytest.approx(
        (current.bank + sum(o["sell_price"] * 10 for o in t["out"])
         - sum(i["price"] * 10 for i in t["in"])) / 10,
        abs=0.05,
    )


def test_hit_gate_strips_a_marginal_hit(rules):
    """A hit must clear hit_ev_threshold on its own marginal net EV."""
    rows = []
    positions = ["GKP", "GKP", "DEF", "DEF", "DEF", "DEF", "DEF",
                 "MID", "MID", "MID", "MID", "MID", "FWD", "FWD", "FWD"]
    for k, position in enumerate(positions):
        rows.append({"id": k + 1, "web_name": f"own{k}", "team": f"T{k % 5}",
                     "position": position, "price": 5.0, "xpts_horizon": 20.0,
                     "xpts_gw2": 4.0})
    rows.append({"id": 98, "web_name": "big", "team": "T8", "position": "MID",
                 "price": 5.0, "xpts_horizon": 35.0, "xpts_gw2": 8.0})
    rows.append({"id": 99, "web_name": "small", "team": "T9", "position": "FWD",
                 "price": 5.0, "xpts_horizon": 24.1, "xpts_gw2": 5.0})
    frame = pd.DataFrame(rows)
    current = CurrentSquad(buy_costs={k + 1: 50 for k in range(15)}, bank=0, free_transfers=1)
    squad, audit = run_live.solve(frame, rules, current, allow_unverified=True)
    assert 98 in squad.transfers_in and 99 not in squad.transfers_in
    assert squad.hits == 0 and audit["hit_gate"].startswith("rejected")


def test_stale_squad_file_errors_clearly(pool, tmp_path):
    path = tmp_path / "squad.json"
    path.write_text(json.dumps({
        "bank": 0, "free_transfers": 1, "players": [{"id": 4242, "buy_cost": 50}],
    }), encoding="utf-8")
    with pytest.raises(SystemExit, match="absent from"):
        run_live.main(["--projections", _write(pool, "stale"), "--squad", str(path),
                       "--allow-unverified"])


# --------------------------------------------------------------------------
# sanity guards
# --------------------------------------------------------------------------

def test_bench_hair_detector_finds_close_calls(rules):
    """A 0.14 margin between the weakest starting DEF and a bench DEF must be
    reported (the GW22 class of leak); the 9-point gaps must not."""
    squad, score, pos = _hand_squad()
    hairs = run_live.bench_hairs(squad, score, pos, rules, fit={}, threshold=0.2)
    assert [(h["xi_id"], h["bench_id"], h["margin"]) for h in hairs] == [(6, 7, 0.14)]
    assert hairs[0]["bench_slot"] == squad.bench.index(7) + 1


def test_bench_hair_detector_skips_unfit_players(rules):
    squad, score, pos = _hand_squad()
    hairs = run_live.bench_hairs(squad, score, pos, rules, fit={7: False}, threshold=0.2)
    assert hairs == []


def test_bench_hair_detector_surfaces_a_costly_override(rules):
    """A negative margin (a force_bench overlay stranding the better player) is
    a hair too — the overlay's price must be visible."""
    squad, score, pos = _hand_squad()
    score[7] = 4.0  # the benched DEF now outscores the starter: margin -0.86
    hairs = run_live.bench_hairs(squad, score, pos, rules, fit={}, threshold=0.2)
    assert hairs[0]["margin"] == pytest.approx(-0.86)


def test_bench_hair_detector_respects_formation_minimums(rules):
    """With exactly the minimum 3 defenders starting, no DEF can be swapped out
    for a bench MID/FWD — those pairs are not legal swaps and must not show."""
    squad, score, pos = _hand_squad(defenders_in_xi=3)
    hairs = run_live.bench_hairs(squad, score, pos, rules, fit={}, threshold=100.0)
    for h in hairs:
        assert not (pos[h["xi_id"]] == "DEF" and pos[h["bench_id"]] != "DEF")


def _hand_squad(defenders_in_xi: int = 4):
    """A hand-built 15 (GKP 1-2, DEF 3-7, MID 8-12, FWD 13-15) with a deliberate
    0.14 hair between the weakest starting DEF (6) and the bench DEF (7)."""
    from fpl_claude.optimize.milp import OptimizedSquad

    pos = {}
    pid = 0
    for position, count in (("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)):
        for _ in range(count):
            pid += 1
            pos[pid] = position

    defs = [3, 4, 5, 6][:defenders_in_xi]
    mids = [8, 9, 10, 11, 12][: 11 - 1 - len(defs) - 2]
    fwds = [13, 14, 15][: 11 - 1 - len(defs) - len(mids)]
    xi = [1] + defs + mids + fwds
    score = {i: (10.0 if i in xi else 1.0) for i in pos}
    score[6] = 3.14 if 6 in xi else score[6]
    score[7] = 3.00
    bench = sorted((i for i in pos if i not in xi and pos[i] != "GKP"), key=lambda i: -score[i])
    bench += [i for i in pos if pos[i] == "GKP" and i not in xi]
    squad = OptimizedSquad(
        squad=list(pos), xi=xi, captain=xi[1], vice=xi[2], bench=bench,
        cost=1000, objective=0.0,
    )
    return squad, score, pos


def test_minutes_and_flag_guards(pool, rules, tmp_path, capsys):
    """Neutral minutes confidence / low_sample rows are surfaced, and an FPL
    flag on a selected player is reported from the bootstrap snapshot."""
    squad, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    picked = int(squad.squad[0])
    bootstrap = tmp_path / "bootstrap.json"
    bootstrap.write_text(json.dumps({"elements": [
        {"id": picked, "status": "d", "chance_of_playing_next_round": 50, "news": "knock"},
    ]}), encoding="utf-8")

    dump = tmp_path / "decision.json"
    run_live.main([
        "--projections", _write(pool, "guards"), "--allow-unverified",
        "--flags", str(bootstrap), "--json", str(dump),
    ])
    out = capsys.readouterr().out
    assert "FPL FLAGS on selected players" in out
    payload = json.loads(dump.read_text(encoding="utf-8"))
    assert [f["id"] for f in payload["guards"]["flagged"]] == [picked]
    assert payload["guards"]["flags_available"] is True

    risky = {r["id"] for r in payload["guards"]["minutes_risk"]}
    expected = {
        int(i) for i in squad.squad
        if pool.set_index("id").loc[i, "minutes_confidence"] == "neutral"
        or bool(pool.set_index("id").loc[i, "low_sample"])
    }
    assert risky == expected


def test_no_flags_switch_says_so(pool, capsys):
    run_live.main(["--projections", _write(pool, "noflags"), "--allow-unverified", "--no-flags"])
    assert "availability UNCHECKED" in capsys.readouterr().out


def test_club_usage_marks_the_cap(pool, rules):
    squad, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    rows = pool.set_index("id").loc[squad.squad].reset_index()
    usage = run_live.club_usage(rows, 3)
    assert sum(u["count"] for u in usage) == 15
    assert all(u["count"] <= 3 for u in usage)
    assert any(u["at_cap"] for u in usage)  # T1 is stacked, the cap must bind


# --------------------------------------------------------------------------
# JSON dump shape
# --------------------------------------------------------------------------

def test_json_dump_shape(pool, rules, tmp_path, capsys):
    banned = int(pool.loc[pool["web_name"] == "T6-GKP0", "id"].iloc[0])
    base, _ = run_live.solve(pool, rules, None, ban=frozenset({banned}), allow_unverified=True)
    dump = tmp_path / "nested" / "decision.json"
    run_live.main([
        "--projections", _write(pool, "shape"), "--allow-unverified",
        "--json", str(dump), "--captain", str(base.vice), "--ban", "T6-GKP0",
    ])
    capsys.readouterr()
    payload = json.loads(dump.read_text(encoding="utf-8"))

    for key in (
        "generated_at_utc", "mode", "dry_run", "season", "ruleset_verified", "sources",
        "score_col", "xi_score_col", "objective", "squad", "xi", "bench_order",
        "captain", "vice", "money", "predicted_xi_xpts", "transfers", "overlay", "guards",
    ):
        assert key in payload, key

    assert payload["mode"] == "initial-build" and payload["transfers"] is None
    assert len(payload["squad"]) == 15 and len(payload["xi"]) == 11
    assert len(payload["bench_order"]) == 4
    assert payload["xi_score_col"] == "xpts_gw1"
    assert set(payload["squad"][0]) >= {
        "id", "web_name", "team", "position", "price", "role", "xpts_gw", "xpts_horizon",
        "ownership_pct", "minutes_confidence", "low_sample", "status",
    }
    assert payload["money"]["bank_m"] == pytest.approx(
        payload["money"]["budget_m"] - payload["money"]["spend_m"], abs=0.01
    )
    # the armband override moved the C, and the solver's captain became the V
    assert payload["captain"]["id"] == base.vice
    assert payload["vice"]["id"] == base.captain
    assert payload["overlay"]["captain"] == payload["captain"]["id"]
    assert banned not in [p["id"] for p in payload["squad"]]  # --ban took a NAME
    for key in ("max_per_club", "club_usage", "bench_hairs", "minutes_risk", "flagged"):
        assert key in payload["guards"], key


def test_dry_run_label_when_ruleset_unverified(pool, monkeypatch, capsys, tmp_path):
    """An unverified ruleset must be shouted about in print AND in the dump."""
    import copy

    real = Ruleset.load("2026-27")
    stale = Ruleset(copy.deepcopy(real.raw))
    stale.raw["chips"]["verify_at_season_launch"] = True
    monkeypatch.setattr(run_live.Ruleset, "load", classmethod(lambda cls, season="x": stale))

    dump = tmp_path / "decision.json"
    run_live.main([
        "--projections", _write(pool, "dry"), "--allow-unverified", "--json", str(dump),
    ])
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "NOT A SUBMITTABLE DECISION" in out
    payload = json.loads(dump.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True and payload["unverified_sections"] == ["chips"]


def test_refuses_unverified_ruleset_without_the_override(pool, monkeypatch):
    import copy

    real = Ruleset.load("2026-27")
    stale = Ruleset(copy.deepcopy(real.raw))
    stale.raw["chips"]["verify_at_season_launch"] = True
    monkeypatch.setattr(run_live.Ruleset, "load", classmethod(lambda cls, season="x": stale))
    with pytest.raises(SystemExit, match="allow-unverified"):
        run_live.main(["--projections", _write(pool, "refuse")])


def test_missing_projections_directory_errors(tmp_path):
    with pytest.raises(SystemExit, match="no projections CSV"):
        run_live.latest_projections(tmp_path)


def test_bad_csv_errors(tmp_path):
    path = tmp_path / "x.csv"
    pd.DataFrame({"id": [1], "web_name": ["a"]}).to_csv(path, index=False)
    with pytest.raises(SystemExit, match="not a projections table"):
        run_live.load_projections(path)


def test_out_survives_a_cp1252_console(monkeypatch, capsys):
    """The Windows failure mode: a strict cp1252 stdout must degrade, not raise."""
    import io

    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict", newline="")
    monkeypatch.setattr(run_live.sys, "stdout", stream)
    # cp1252 covers ö/é/ã but NOT ń — Zieliński is the name that actually raises.
    run_live._out("Zieliński / Gyökeres / João Pedro")
    stream.flush()
    text = buffer.getvalue().decode("cp1252")
    assert "Zieli?ski" in text and "Gyökeres" in text and "João Pedro" in text


def test_optimize_and_run_live_agree_on_the_squad(pool, rules):
    """run_live.solve is a thin policy wrapper: for an initial build it must
    return exactly what optimize() returns."""
    direct = optimize(pool, rules, allow_unverified=True)
    wrapped, _ = run_live.solve(pool, rules, None, allow_unverified=True)
    assert wrapped.squad == direct.squad and wrapped.captain == direct.captain

"""Level / captain calibration decomposition for the 2025/26 backtest (defect A2).

Regenerates every table quoted in `reports/backtest/2025-26/calibration.md`.

    PYTHONPATH=src python notebooks/calibration_analysis.py

Reads only the committed, append-only per-GW players CSVs
(`reports/backtest/2025-26/gwNN_players.csv`, columns: id, web_name, team,
position, price, predicted, actual, minutes, role[C/V/XI/bench],
played_after_subs) plus the single hit the season took (GW2, -4). No model code
is imported: this is a pure post-hoc decomposition of predicted-vs-actual, so it
stays reproducible verbatim even as the live pipeline evolves.

Error convention throughout: **error = actual - predicted**, so a POSITIVE error
means the model UNDER-predicted (the week out-scored the projection). This
matches the reviews' calibration logs (GW1 +28.7, GW11 -19.0, ...).

Decomposition of the reported per-GW error (memo Outcome line):

    memo_err = base_XI_err + captain_slot_err + autosub_gain - hit

  base_XI_err      picked XI (11), captain counted ONCE: sum(actual-predicted)
  captain_slot_err the doubled EXTRA copy: actual[eff captain] - predicted[picked C]
  autosub_gain     wedge: post-autosub XI actual - picked XI actual (>= 0)
  hit              wedge: points deducted for a -4 (GW2 only, all season)

An interpretability re-cut of the same total splits the captain 0+2 instead of
1+1: non-captain XI (10) + full doubled captain (2x).
"""

from __future__ import annotations

import statistics as st
from pathlib import Path

import pandas as pd

REPORTS = Path(__file__).resolve().parent.parent / "reports" / "backtest" / "2025-26"
GWS = range(1, 21)
HITS = {2: 4}  # GW -> points deducted; only GW2 took a hit all season

# Committed memo Outcome numbers, for an exact reconciliation check (the script
# must reproduce these from the CSVs or the decomposition is not faithful).
COMMITTED_PRED = {
    1: 55.31, 2: 59.01, 3: 51.06, 4: 51.46, 5: 51.78, 6: 53.12, 7: 57.85,
    8: 53.84, 9: 53.99, 10: 53.74, 11: 53.0, 12: 55.23, 13: 59.39, 14: 52.79,
    15: 52.48, 16: 48.92, 17: 58.47, 18: 54.74, 19: 50.23, 20: 49.74,
}
COMMITTED_ACT = {
    1: 84, 2: 44, 3: 54, 4: 61, 5: 40, 6: 55, 7: 71, 8: 82, 9: 58, 10: 75,
    11: 34, 12: 42, 13: 44, 14: 69, 15: 56, 16: 72, 17: 70, 18: 43, 19: 62,
    20: 63,
}

# Official 2025/26 GW league averages (all 11M managers), from knowledge.md /
# season context — used only to compare weekly-level dispersion (can an
# "environment-level" term even track the slate swing?).
LEAGUE_AVG = {
    1: 54, 2: 51, 3: 48, 4: 63, 5: 42, 6: 46, 7: 60, 8: 56, 9: 46, 10: 65,
    11: 38, 12: 39, 13: 35, 14: 58, 15: 49, 16: 60, 17: 66, 18: 44, 19: 40,
    20: 42,
}


def load_gw(gw: int) -> pd.DataFrame:
    return pd.read_csv(REPORTS / f"gw{gw:02d}_players.csv")


def decompose() -> pd.DataFrame:
    rows = []
    for gw in GWS:
        df = load_gw(gw)
        xi = df[df.role.isin(["C", "V", "XI"])]
        cap = df[df.role == "C"].iloc[0]
        vice = df[df.role == "V"].iloc[0]

        # Effective captain: picked captain if he played >0', else vice if he
        # played, else the (blanking) captain stays doubled at 0.
        if cap.minutes > 0:
            eff = cap
        elif vice.minutes > 0:
            eff = vice
        else:
            eff = cap

        base_pred = float(xi.predicted.sum())          # 11 players, captain once
        base_act = float(xi.actual.sum())
        cap_pred_extra = float(cap.predicted)           # the doubled extra copy
        cap_act_extra = float(eff.actual)

        post = df[df.played_after_subs]
        hit = HITS.get(gw, 0)
        memo_pred = base_pred + cap_pred_extra
        memo_act_pre_hit = float(post.actual.sum()) + cap_act_extra
        memo_act = memo_act_pre_hit - hit
        autosub_gain = float(post.actual.sum()) - base_act

        rows.append(
            {
                "gw": gw,
                "cap": cap.web_name,
                "eff_cap": eff.web_name,
                "cap_switched": bool(eff.id != cap.id),
                # task-defined split: base (cap x1) + captain extra (x1)
                "base_pred": base_pred,
                "base_act": base_act,
                "base_err": base_act - base_pred,
                "cap_pred_extra": cap_pred_extra,
                "cap_act_extra": cap_act_extra,
                "cap_slot_err": cap_act_extra - cap_pred_extra,
                # interpretability re-cut: non-captain-10 + full doubled captain
                "noncap_pred": base_pred - float(cap.predicted),
                "noncap_act": base_act - float(cap.actual),
                "noncap_err": (base_act - float(cap.actual))
                - (base_pred - float(cap.predicted)),
                "cap_full_pred": 2 * cap_pred_extra,
                "cap_full_act": 2 * cap_act_extra,
                "cap_full_err": 2 * (cap_act_extra - cap_pred_extra),
                # captain single (one copy), the per-player calibration view
                "cap_single_pred": float(cap.predicted),
                "cap_single_act": cap_act_extra,
                "cap_single_err": cap_act_extra - float(cap.predicted),
                # wedges + reconciliation
                "autosub_gain": autosub_gain,
                "hit": hit,
                "memo_pred": memo_pred,
                "memo_act": memo_act,
                "memo_err": memo_act - memo_pred,
                "league_avg": LEAGUE_AVG[gw],
            }
        )
    return pd.DataFrame(rows)


def reconcile(d: pd.DataFrame) -> None:
    print("=" * 78)
    print("RECONCILIATION — reconstructed vs committed memo Outcome numbers")
    print("=" * 78)
    print(f"{'GW':>3} {'pred(recon)':>11} {'pred(memo)':>10} "
          f"{'act(recon)':>10} {'act(memo)':>9} {'ok':>4}")
    all_ok = True
    for _, r in d.iterrows():
        gw = int(r.gw)
        pred_ok = round(r.memo_pred, 2) == COMMITTED_PRED[gw]
        act_ok = int(r.memo_act) == COMMITTED_ACT[gw]
        ok = pred_ok and act_ok
        all_ok &= ok
        print(f"{gw:>3} {r.memo_pred:>11.2f} {COMMITTED_PRED[gw]:>10.2f} "
              f"{int(r.memo_act):>10d} {COMMITTED_ACT[gw]:>9d} {'y' if ok else 'N':>4}")
    print(f"\nAll 20 GWs reconcile exactly: {all_ok}")
    print(f"Captain ever handed off to vice (0' blank): {bool(d.cap_switched.any())}")
    assert all_ok, "reconstruction does not match committed memos — decomposition unfaithful"


def summ(name: str, s: pd.Series) -> dict:
    v = s.astype(float).tolist()
    return {
        "component": name,
        "mean": st.mean(v),
        "median": st.median(v),
        "std": st.pstdev(v),          # population std over the 20-GW sample
        "min": min(v),
        "max": max(v),
        "mae": st.mean([abs(x) for x in v]),
    }


def stats_table(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("COMPONENT STATISTICS over 20 GWs  (error = actual - predicted)")
    print("=" * 78)
    comps = [
        ("memo_err (reported total)", d.memo_err),
        ("  base_XI_err (cap x1)", d.base_err),
        ("  captain_slot_err (extra copy)", d.cap_slot_err),
        ("  autosub_gain (wedge)", d.autosub_gain),
        ("  hit (wedge)", -d.hit),  # enters memo_err as -hit
        ("re-cut: noncap_XI_err (10)", d.noncap_err),
        ("re-cut: captain_full_err (2x)", d.cap_full_err),
        ("captain_single_err (1x)", d.cap_single_err),
    ]
    hdr = f"{'component':<34}{'mean':>8}{'median':>8}{'std':>8}{'min':>8}{'max':>8}{'MAE':>8}"
    print(hdr)
    print("-" * len(hdr))
    for name, s in comps:
        r = summ(name, s)
        print(f"{name:<34}{r['mean']:>8.2f}{r['median']:>8.2f}{r['std']:>8.2f}"
              f"{r['min']:>8.2f}{r['max']:>8.2f}{r['mae']:>8.2f}")

    # identity check: memo_err == base_err + cap_slot_err + autosub_gain - hit
    resid = (d.memo_err - (d.base_err + d.cap_slot_err + d.autosub_gain - d.hit)).abs().max()
    print(f"\nidentity max |residual| (memo_err vs sum of parts): {resid:.6f}")


def variance_share(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("VARIANCE DECOMPOSITION of the clean (wedge-free) error")
    print("=" * 78)
    # clean error = noncap_err + cap_full_err  (a partition of the doubled XI err)
    a = d.noncap_err.astype(float)
    b = d.cap_full_err.astype(float)
    clean = a + b
    va, vb = st.pvariance(a.tolist()), st.pvariance(b.tolist())
    # population covariance
    ma, mb = st.mean(a.tolist()), st.mean(b.tolist())
    cov = st.mean([(x - ma) * (y - mb) for x, y in zip(a, b)])
    vclean = st.pvariance(clean.tolist())
    print(f"Var(non-captain XI, 10)      = {va:8.2f}   ({100*va/vclean:5.1f}% of clean var)")
    print(f"Var(captain full, 2x)        = {vb:8.2f}   ({100*vb/vclean:5.1f}% of clean var)")
    print(f"2*Cov(noncap, captain)       = {2*cov:8.2f}   ({100*2*cov/vclean:5.1f}% of clean var)")
    print(f"Var(clean total)             = {vclean:8.2f}")
    print(f"\nStd(non-captain XI)          = {va**0.5:6.2f}")
    print(f"Std(captain full 2x)         = {vb**0.5:6.2f}")
    print(f"Std(clean total)             = {vclean**0.5:6.2f}")
    # counterfactual: spread if the captain slot were predicted perfectly
    cf = (d.memo_err - d.cap_slot_err).astype(float)
    print(f"\nStd(memo_err) as reported                 = {st.pstdev(d.memo_err.tolist()):6.2f}")
    print(f"Std(memo_err) if captain slot were exact  = {st.pstdev(cf.tolist()):6.2f}"
          "   (removing the extra copy's error)")
    # remove full captain influence: memo_err minus cap_full_err leaves noncap+wedges
    cf2 = (d.memo_err - d.cap_full_err).astype(float)
    print(f"Std(memo_err) if WHOLE captain were exact = {st.pstdev(cf2.tolist()):6.2f}"
          "   (removing both copies' error)")


def dispersion(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("WEEKLY-LEVEL DISPERSION — can an 'environment-level' term track the slate?")
    print("=" * 78)
    print(f"Std(predicted XI total)   = {st.pstdev(d.memo_pred.tolist()):6.2f}   "
          f"(mean {st.mean(d.memo_pred.tolist()):.1f})")
    print(f"Std(actual XI total)      = {st.pstdev(d.memo_act.tolist()):6.2f}   "
          f"(mean {st.mean(d.memo_act.tolist()):.1f})")
    print(f"Std(league GW average)    = {st.pstdev(list(LEAGUE_AVG.values())):6.2f}   "
          f"(mean {st.mean(list(LEAGUE_AVG.values())):.1f})")

    def corr(x, y):
        mx, my = st.mean(x), st.mean(y)
        cov = st.mean([(a - mx) * (b - my) for a, b in zip(x, y)])
        sx, sy = st.pstdev(x), st.pstdev(y)
        return cov / (sx * sy) if sx and sy else float("nan")

    pred = d.memo_pred.tolist()
    act = d.memo_act.tolist()
    lg = d.league_avg.tolist()
    print(f"\ncorr(our predicted, league avg)  = {corr(pred, lg):+.2f}")
    print(f"corr(our predicted, our actual)  = {corr(pred, act):+.2f}")
    print(f"corr(league avg, our actual)     = {corr(lg, act):+.2f}")
    print("\nRead: our prediction is far TIGHTER than realised weekly outcomes — the")
    print("correct property of a mean estimate E[X] (Var(E[X]) <= Var(X)). The slate")
    print("swing is not a fixed offset a scale term could remove; it is week-level")
    print("outcome variance already conditioned on fixtures.")


def tails(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("TWO-TAILS — the extreme weeks, attributed to base vs captain")
    print("=" * 78)
    s = d.sort_values("memo_err")
    hdr = (f"{'GW':>3}{'memo_err':>9}{'base_err':>9}{'cap_slot':>9}"
           f"{'cap_full':>9}{'autosub':>8}{'cap':>9}{'capd1x':>9}")
    print(hdr)
    print("-" * len(hdr))
    for _, r in s.iterrows():
        print(f"{int(r.gw):>3}{r.memo_err:>9.1f}{r.base_err:>9.1f}{r.cap_slot_err:>9.1f}"
              f"{r.cap_full_err:>9.1f}{r.autosub_gain:>8.1f}{r.cap:>9}{r.cap_single_err:>9.1f}")
    worst = d.reindex(d.memo_err.abs().sort_values(ascending=False).index).head(6)
    print("\nSix largest |memo_err| weeks — captain's share of the reported error:")
    for _, r in worst.iterrows():
        share = 100 * r.cap_full_err / r.memo_err if r.memo_err else float("nan")
        print(f"  GW{int(r.gw):>2}: memo_err {r.memo_err:+6.1f} | captain(2x) {r.cap_full_err:+6.1f} "
              f"| base {r.base_err:+5.1f} | captain share {share:5.0f}%")


def by_position(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("BY-POSITION per-player error on the picked XI (pooled over 20 GWs)")
    print("=" * 78)
    allrows = []
    for gw in GWS:
        df = load_gw(gw)
        xi = df[df.role.isin(["C", "V", "XI"])].copy()
        xi["err"] = xi.actual - xi.predicted
        xi["gw"] = gw
        allrows.append(xi)
    pool = pd.concat(allrows, ignore_index=True)
    print(f"{'position':<10}{'n':>5}{'mean_pred':>11}{'mean_act':>10}{'mean_err':>10}{'MAE':>8}")
    print("-" * 54)
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        g = pool[pool.position == pos]
        print(f"{pos:<10}{len(g):>5}{g.predicted.mean():>11.2f}{g.actual.mean():>10.2f}"
              f"{g.err.mean():>10.2f}{g.err.abs().mean():>8.2f}")
    print(f"{'ALL XI':<10}{len(pool):>5}{pool.predicted.mean():>11.2f}{pool.actual.mean():>10.2f}"
          f"{pool.err.mean():>10.2f}{pool.err.abs().mean():>8.2f}")

    print("\nStarters only (minutes >= 60) — isolates scoring-rate level from minutes risk:")
    print(f"{'position':<10}{'n':>5}{'mean_pred':>11}{'mean_act':>10}{'mean_err':>10}{'MAE':>8}")
    print("-" * 54)
    started = pool[pool.minutes >= 60]
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        g = started[started.position == pos]
        if len(g):
            print(f"{pos:<10}{len(g):>5}{g.predicted.mean():>11.2f}{g.actual.mean():>10.2f}"
                  f"{g.err.mean():>10.2f}{g.err.abs().mean():>8.2f}")
    print(f"{'ALL start':<10}{len(started):>5}{started.predicted.mean():>11.2f}"
          f"{started.actual.mean():>10.2f}{started.err.mean():>10.2f}{started.err.abs().mean():>8.2f}")

    nc = started[started.role != "C"]
    print(f"\nNon-captain starters (min>=60): n={len(nc)}  mean_err={nc.err.mean():+.2f}  "
          f"MAE={nc.err.abs().mean():.2f}  mean_pred={nc.predicted.mean():.2f}  "
          f"mean_act={nc.actual.mean():.2f}")
    caps = pool[pool.role == "C"]
    cap_std = st.pstdev((caps.actual - caps.predicted).tolist())
    print(f"Captain single (as picked):     n={len(caps)}  mean_err={caps.err.mean():+.2f}  "
          f"MAE={caps.err.abs().mean():.2f}  mean_pred={caps.predicted.mean():.2f}  "
          f"mean_act={caps.actual.mean():.2f}  std_err={cap_std:.2f}")


def season_headline(d: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("SEASON HEADLINE")
    print("=" * 78)
    print(f"Sum predicted XI (incl cap double) = {d.memo_pred.sum():.1f}")
    print(f"Sum actual (after autosubs & hits) = {d.memo_act.sum():.0f}  (season total, matches 1179)")
    print(f"20-GW mean memo_err                = {d.memo_err.mean():+.2f}")
    print(f"20-GW median memo_err              = {d.memo_err.median():+.2f}")
    print(f"20-GW mean base_XI_err (cap x1)    = {d.base_err.mean():+.2f}  "
          f"(std {st.pstdev(d.base_err.tolist()):.2f})")
    print(f"20-GW mean captain_slot_err (x1)   = {d.cap_slot_err.mean():+.2f}  "
          f"(std {st.pstdev(d.cap_slot_err.tolist()):.2f})")
    print(f"20-GW mean noncap_XI_err (10)      = {d.noncap_err.mean():+.2f}  "
          f"(std {st.pstdev(d.noncap_err.tolist()):.2f})")
    print(f"20-GW mean captain_full_err (2x)   = {d.cap_full_err.mean():+.2f}  "
          f"(std {st.pstdev(d.cap_full_err.tolist()):.2f})")
    print(f"Total autosub_gain over season     = {d.autosub_gain.sum():.0f}  "
          f"(mean {d.autosub_gain.mean():.2f}/GW)")
    print(f"Total hits over season             = {d.hit.sum():.0f}  (GW2 only)")

    import math
    n = len(d)
    print("\nIs any mean bias distinguishable from zero? (sample SE, one-sample t)")
    for label, s in [
        ("base_XI_err (cap x1)", d.base_err),
        ("noncap_XI_err (10)", d.noncap_err),
        ("captain_slot_err (1x)", d.cap_slot_err),
        ("captain_full_err (2x)", d.cap_full_err),
    ]:
        vals = s.astype(float).tolist()
        m = st.mean(vals)
        se = st.stdev(vals) / math.sqrt(n)  # sample std / sqrt(n)
        t = m / se if se else float("nan")
        print(f"  {label:<24} mean {m:+6.2f}   SE {se:4.2f}   t {t:+5.2f}   "
              f"({'sig' if abs(t) >= 2.09 else 'NOT sig'} at 5%, df={n - 1})")


def main() -> None:
    d = decompose()
    reconcile(d)
    season_headline(d)
    stats_table(d)
    variance_share(d)
    dispersion(d)
    tails(d)
    by_position(d)
    print("\n(analysis complete)")


if __name__ == "__main__":
    main()

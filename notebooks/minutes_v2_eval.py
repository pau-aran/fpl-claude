"""Minutes v2 vs v1 on the 2025-26 holdout — every table in the report (A6).

Regenerates `reports/models/minutes-v2.md`. Nothing here trains: it loads the
artifact written by `python -m fpl_claude.models.minutes_v2 --train`, rebuilds
the holdout features point-in-time, and scores both models on the SAME rows.

    PYTHONPATH=src python notebooks/minutes_v2_eval.py [--data-root db/vaastav]
        [--model db/models/minutes_v2.joblib]

Why slices and not just a headline number: an aggregate log loss can improve
while the model gets *worse* exactly where decisions are made. The weeks that
cost this team points in the 2025-26 backtest were the congested festive round,
the AFCON window and the European midweeks — so those are the cuts that matter,
alongside the rotation-prone band (start share 0.3-0.8) where bench order is
actually decided. A model that only beats v1 on nailed 90-minute men has
improved nothing we didn't already know.

Every metric is on the *same* population: rows with at least some history
(cold starts are excluded from both, because v2 refuses to predict them and
falls back to v1 by design).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fpl_claude.models import minutes_v2 as m2

HOLDOUT = m2.HOLDOUT_SEASON


def _fmt(rows: list[dict], cols: list[str]) -> str:
    df = pd.DataFrame(rows)[cols]
    return df.to_string(index=False)


def headline(holdout: pd.DataFrame, v2: pd.DataFrame, v1: pd.DataFrame) -> None:
    print("=" * 78)
    print(f"HEADLINE — {HOLDOUT} holdout, n={len(holdout):,} player-fixtures")
    print("=" * 78)
    rows = []
    for label, y, pv1, pv2 in (
        ("p_start", holdout.y_start, v1.p_start, v2.p_start),
        ("p60", holdout.y_p60, v1.p60, v2.p60),
    ):
        a = m2.classification_metrics(y.to_numpy(), pv1.to_numpy())
        b = m2.classification_metrics(y.to_numpy(), pv2.to_numpy())
        rows.append(
            {
                "target": label, "base_rate": a["base_rate"],
                "v1_logloss": a["log_loss"], "v2_logloss": b["log_loss"],
                "v1_brier": a["brier"], "v2_brier": b["brier"],
                "v1_auc": a["auc"], "v2_auc": b["auc"],
            }
        )
    print(_fmt(rows, list(rows[0])))
    y = holdout.y_minutes.to_numpy()
    a = m2.regression_metrics(y, v1.exp_minutes.to_numpy())
    b = m2.regression_metrics(y, v2.exp_minutes.to_numpy())
    print("\nexpected minutes")
    print(_fmt([{"model": "v1", **a}, {"model": "v2", **b}], ["model", "mae", "rmse", "bias"]))


def calibration(holdout: pd.DataFrame, v2: pd.DataFrame, v1: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("CALIBRATION BY DECILE of predicted probability (p_start)")
    print("=" * 78)
    for name, pred in (("v1", v1.p_start), ("v2", v2.p_start)):
        tab = m2.calibration_table(holdout.y_start.to_numpy(), pred.to_numpy())
        print(f"\n{name}")
        print(_fmt(tab, ["decile", "n", "mean_pred", "actual"]))
    print("\n" + "=" * 78)
    print("CALIBRATION BY DECILE (p60)")
    print("=" * 78)
    for name, pred in (("v1", v1.p60), ("v2", v2.p60)):
        tab = m2.calibration_table(holdout.y_p60.to_numpy(), pred.to_numpy())
        print(f"\n{name}")
        print(_fmt(tab, ["decile", "n", "mean_pred", "actual"]))


def _slice_row(name: str, d: pd.DataFrame, v2: pd.DataFrame, v1: pd.DataFrame) -> dict:
    y_s, y_6, y_m = d.y_start.to_numpy(), d.y_p60.to_numpy(), d.y_minutes.to_numpy()
    a_s = m2.classification_metrics(y_s, v1.p_start.to_numpy())
    b_s = m2.classification_metrics(y_s, v2.p_start.to_numpy())
    a_6 = m2.classification_metrics(y_6, v1.p60.to_numpy())
    b_6 = m2.classification_metrics(y_6, v2.p60.to_numpy())
    a_m = m2.regression_metrics(y_m, v1.exp_minutes.to_numpy())
    b_m = m2.regression_metrics(y_m, v2.exp_minutes.to_numpy())
    return {
        "slice": name, "n": len(d), "base": a_s["base_rate"],
        "v1_ll_start": a_s["log_loss"], "v2_ll_start": b_s["log_loss"],
        "v1_ll_p60": a_6["log_loss"], "v2_ll_p60": b_6["log_loss"],
        "v1_mae_min": a_m["mae"], "v2_mae_min": b_m["mae"],
    }


def slices(holdout: pd.DataFrame, v2: pd.DataFrame, v1: pd.DataFrame) -> None:
    print("\n" + "=" * 78)
    print("SLICES — where the decisions actually get made")
    print("=" * 78)
    h = holdout
    # Rotation band on the TRUTH-adjacent side: the player's own recent start
    # share (a feature, not an outcome), so the slice is defined by what we knew.
    band = h.start_share_5.fillna(0.5)
    cuts = [
        ("ALL", pd.Series(True, index=h.index)),
        ("congested (<=4 rest days)", h.days_since_prev <= 4),
        ("normal rest (5-8 days)", h.days_since_prev.between(5, 8)),
        ("long rest (>8 days)", h.days_since_prev > 8),
        ("3+ fixtures in prior 14d", h.team_fix_last_14 >= 3),
        ("midweek kickoff", h.is_midweek == 1),
        ("AFCON window", h.afcon_window == 1),
        ("Euro-week clubs (in UEFA period)", h.euro_week == 1),
        ("post international break", h.intl_break_prev == 1),
        ("nailed (start share5 >= 0.8)", band >= 0.8),
        ("rotation-prone (0.3-0.8)", band.between(0.3, 0.8, inclusive="left")),
        ("fringe (< 0.3)", band < 0.3),
        ("GKP", h.element_type == 1),
        ("DEF", h.element_type == 2),
        ("MID", h.element_type == 3),
        ("FWD", h.element_type == 4),
    ]
    rows = []
    for name, mask in cuts:
        mask = mask.fillna(False)
        if mask.sum() < 100:
            continue
        rows.append(_slice_row(name, h[mask], v2[mask], v1[mask]))
    print(_fmt(rows, list(rows[0])))


def bench_order(holdout: pd.DataFrame, v2: pd.DataFrame, v1: pd.DataFrame) -> None:
    """The FPL-relevant read: does v2 order players better within a gameweek?

    Bench order is a ranking problem — the autosub only needs the 12th man to be
    likelier to play than the 13th. Pairwise concordance within a GW measures
    exactly that, and it is the number that turns a log-loss win into points.
    """
    print("\n" + "=" * 78)
    print("BENCH-ORDER READ — within-gameweek ranking of P(plays 60+)")
    print("=" * 78)
    rows = []
    for name, pred in (("v1", v1.p60), ("v2", v2.p60)):
        aucs, ns = [], []
        for idx in holdout.groupby("gw").groups.values():
            y = holdout.loc[idx, "y_p60"].to_numpy()
            if y.min() == y.max():
                continue
            aucs.append(m2._auc(y, pred.loc[idx].to_numpy()))
            ns.append(len(idx))
        rows.append(
            {
                "model": name, "gws": len(aucs),
                "mean_within_gw_auc": round(float(np.mean(aucs)), 4),
                "worst_gw_auc": round(float(np.min(aucs)), 4),
            }
        )
    print(_fmt(rows, ["model", "gws", "mean_within_gw_auc", "worst_gw_auc"]))

    # Points-relevant framing: a starting-XI slot is worth ~2 appearance points
    # plus the whole scoring distribution. Mis-ranking the 11th and 12th man is
    # the concrete cost, so measure the error on the players who matter: those
    # the market owns (top ownership decile), where our XI is actually drawn.
    owned = holdout[holdout.selected_log >= holdout.selected_log.quantile(0.9)]
    print(f"\nTop-ownership decile only (n={len(owned):,}) — the pool our XI comes from")
    rows = []
    for name, pred in (("v1", v1), ("v2", v2)):
        rows.append(
            {
                "model": name,
                **m2.classification_metrics(
                    owned.y_p60.to_numpy(), pred.loc[owned.index, "p60"].to_numpy()
                ),
            }
        )
    print(_fmt(rows, ["model", "log_loss", "brier", "auc", "mean_pred", "base_rate"]))

    # And the blunt one: how often does each model put >0.5 on a player who
    # ended up with zero minutes (the benching that costs a full XI slot)?
    print("\nConfident-and-wrong rate (p_start > 0.5 but 0 minutes played)")
    rows = []
    for name, pred in (("v1", v1.p_start), ("v2", v2.p_start)):
        conf = pred > 0.5
        blanked = (holdout.y_play == 0) & conf
        rows.append(
            {
                "model": name, "confident_rows": int(conf.sum()),
                "blanked": int(blanked.sum()),
                "rate": round(float(blanked.sum() / max(1, conf.sum())), 4),
            }
        )
    print(_fmt(rows, ["model", "confident_rows", "blanked", "rate"]))


def importances(model: m2.MinutesModelV2) -> None:
    print("\n" + "=" * 78)
    print("FEATURE IMPORTANCE (gain) — p_start head, top 20")
    print("=" * 78)
    imp = pd.Series(
        model.boosters["p_start"].feature_importance("gain"), index=list(model.features)
    ).sort_values(ascending=False)
    total = imp.sum()
    for name, gain in imp.head(20).items():
        print(f"  {name:<24}{gain:>12,.0f}  {100 * gain / total:>5.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="db/vaastav")
    parser.add_argument("--model", default=str(m2.DEFAULT_ARTIFACT))
    args = parser.parse_args()

    model = m2.load_model(Path(args.model))
    if model is None:
        raise SystemExit(
            f"no usable artifact at {args.model} — run "
            "`python -m fpl_claude.models.minutes_v2 --train` first"
        )
    holdout = m2.dataset_for_season(args.data_root, HOLDOUT)
    holdout = holdout[holdout.is_cold_start == 0].reset_index(drop=True)
    v2 = model.predict_frame(holdout)
    v1 = m2.v1_baseline(holdout)

    print(f"model meta: {model.meta}")
    print(f"cameo minutes constant: {model.cameo_minutes}")
    cold = m2.dataset_for_season(args.data_root, HOLDOUT)
    print(
        f"cold-start rows excluded (v2 declines, v1 prior path used): "
        f"{int(cold.is_cold_start.sum()):,} of {len(cold):,}"
    )
    headline(holdout, v2, v1)
    calibration(holdout, v2, v1)
    slices(holdout, v2, v1)
    bench_order(holdout, v2, v1)
    importances(model)
    print("\n(analysis complete)")


if __name__ == "__main__":
    main()

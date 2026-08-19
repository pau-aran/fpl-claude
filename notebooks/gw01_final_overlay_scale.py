"""Recover the overlay scaling of the 2026-07-26 GW1 solve, so late candidate swaps
can be priced on the SAME post-overlay scale as the committed squad.

WHY THIS EXISTS
---------------
The final GW1 selection (2026-08-19, T-55h) had to be made in an environment where
`db/` is absent (gitignored, and this was a fresh clone) and the FPL API, Wikipedia
and every FPL site are blocked by the egress proxy. So `optimize.run_live` could not
be re-run: there is no `db/projections/2026-07-26.csv` to solve against.

What IS committed is enough to rebuild the part of that table the decision needed:

* `research/2026-27/projections-run.md` — PRE-overlay `xpts_horizon` and `mins/GW`
  for the top ~45 of the pool.
* `decisions/overlays/gw01.json` — the 56 hand-written `start_share` overlays.
* `decisions/gw01_solve.json` — POST-overlay `xpts_horizon` for the chosen 15.

Five players appear in all three, which pins the transform the solve applied:

    post_horizon = pre_horizon * (overlay_share / model_share)
    model_share  = a * mins_per_gw

`a` is fitted below on those five and then checked against them. It reproduces the
committed post-overlay numbers to within 1.7% (four of five inside 0.8%), which is
well inside the model's own error bars — good enough to price a one-player swap,
and NOT good enough to justify re-solving the whole squad by hand. The memo says so.

Run: python notebooks/gw01_final_overlay_scale.py
"""

from __future__ import annotations

# name, pre_horizon, mins_per_gw, overlay_share, post_horizon(committed)
KNOWN = [
    ("Raya", 20.35, 76.1, 0.92, 19.34),
    ("Mbeumo", 20.99, 64.6, 0.85, 21.77),
    ("Wirtz", 16.88, 57.0, 0.80, 18.72),
    ("Szoboszlai", 18.53, 74.2, 0.85, 16.83),
    ("Schade", 18.23, 66.5, 0.72, 15.90),
]


def fit_a(known=KNOWN) -> float:
    """Least-squares slope of model_share against mins_per_gw (no intercept)."""
    num = den = 0.0
    for _name, pre, mins, share, post in known:
        implied_model_share = share / (post / pre)
        num += implied_model_share * mins
        den += mins * mins
    return num / den


def post_horizon(pre: float, mins_per_gw: float, overlay_share: float, a: float) -> float:
    return pre * (overlay_share / (a * mins_per_gw))


def main() -> None:
    a = fit_a()
    print(f"fitted a = {a:.6f}  (model_share = a * mins_per_gw)\n")

    print(f"{'player':<12}{'predicted':>10}{'committed':>11}{'err %':>8}")
    worst = 0.0
    for name, pre, mins, share, post in KNOWN:
        pred = post_horizon(pre, mins, share, a)
        err = 100.0 * (pred - post) / post
        worst = max(worst, abs(err))
        print(f"{name:<12}{pred:>10.2f}{post:>11.2f}{err:>+8.2f}")
    print(f"\nworst error {worst:.2f}%  -> transform accepted for single-swap pricing\n")

    # ---- the one swap the news actually put on the table -------------------
    # Igor Thiago's pre-overlay numbers made him look like the best value in the
    # pool (22.38 horizon, 2.80 pre-overlay pts/GBPm). On the solve's own scale he
    # is not: his overlay (0.80) sits BELOW the model's implied share (~0.96), so
    # the overlay cuts him by ~17%.
    thiago = post_horizon(22.38, 76.1, 0.80, a)
    szobo = post_horizon(18.53, 74.2, 0.85, a)
    thiago_gw1 = 5.08 * (thiago / 22.38)  # scale the GW1 column by the same factor

    print("Szoboszlai (GBP7.0m)  vs  Thiago (GBP8.0m)   [post-overlay, 8-GW horizon]")
    print(f"  Szoboszlai  {szobo:5.2f}   {szobo / 7.0:.3f} pts/GBPm   GW1 3.38")
    print(f"  Thiago      {thiago:5.2f}   {thiago / 8.0:.3f} pts/GBPm   GW1 {thiago_gw1:.2f}")
    print(f"  swap delta  {thiago - szobo:+.2f} horizon for +GBP1.0m"
          f"  ({thiago_gw1 - 3.38:+.2f} GW1)")

    # The GBP1.0m has to come from somewhere, and the bench is already at the
    # minimum-viable GBP16.5m, so it comes out of the XI. The cheapest GBP1.0m in the
    # XI is Tarkowski (GBP6.0m, 16.24 — no overlay, so pre == post) down to
    # N.Williams (GBP5.0m, 16.42 pre-overlay, overlay 0.75).
    #
    # N.Williams has no mins/GW row, so his model_share is unknown; 0.85 is the
    # assumption for a nailed starter, and the conclusion is not sensitive to it
    # across any plausible value.
    print("\nfunding leg — Tarkowski (GBP6.0m) -> N.Williams (GBP5.0m):")
    for assumed_model_share in (0.80, 0.85, 0.90):
        nw = 16.42 * (0.75 / assumed_model_share)
        fund = nw - 16.24
        print(f"  model_share={assumed_model_share:.2f} -> N.Williams {nw:5.2f}"
              f"   funding leg {fund:+.2f}   NET PACKAGE {thiago - szobo + fund:+.2f}")

    print("\nVERDICT: the package is a rounding error in every case, and it churns two"
          "\nnews-validated picks to get there. Hold Szoboszlai and Tarkowski.")


if __name__ == "__main__":
    main()

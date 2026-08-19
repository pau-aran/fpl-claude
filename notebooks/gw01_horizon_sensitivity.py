"""Does a 3-GW objective beat the committed 8-GW one for the season opener?

THE QUESTION (owner, 2026-08-19): "what if we look at the start for 3 GW instead of 8,
since the beginning of the season needs more power?"

METHOD
------
Same constraint as `gw01_final_overlay_scale.py`: no `db/` and no FPL API in this
environment, so the projections table cannot be regenerated. This instead decomposes the
committed per-player 8-GW totals into a per-gameweek series and re-optimises the XI under
different horizons:

    xpts_g  = base * m(FDR_g) * share_g          m(f) = exp(-K * (f - 3))
    share_g = overlay  if g <= duration_gws  else the model's own share

`base` is pinned so the decayed 8-GW sum reproduces the committed pre-overlay horizon, and
`K` (the fixture sensitivity) is fitted on the eleven owned players whose committed GW1 xPts
are known. Overlay `duration_gws` is honoured per gameweek, which is the crux: a duration-3
World Cup fade covers 3/8 of an 8-GW window but 3/3 of a 3-GW one.

The instrument optimises the STARTING XI at a fixed minimum-price bench (the bench is
horizon-invariant - four non-starters at the positional price floor) over the ~45-player pool
recoverable from `research/2026-27/projections-run.md`.

HEADLINE RESULTS
----------------
1. The premise is half-right. The existing 0.85 decay ALREADY puts 53% of the 8-GW objective
   in GW1-3 and 66% in GW1-4. The squad is not "optimised for GW8".
2. Tightening the decay (0.85 -> 0.80 -> 0.75 -> 0.70) changes NOTHING: identical XI at all
   four. Front-loading via decay is a no-op.
3. A 5-GW captaincy-aware window reproduces our committed XI EXACTLY, 11/11, Haaland
   captain. Our squad already behaves like a 5-GW-optimal squad, because the manager overlay
   refused the pure 8-GW solve - which wants B.Fernandes + Joao Pedro and ejects Haaland.
   That is the memo's V4 warning, reproduced here independently.
4. A 3-GW window changes 2 of 11: in Kelleher + Thiago, out Raya + Szoboszlai. Worth about
   +0.2 decayed points - and it sells Raya, the most news-validated pick in the build.
5. THE DECISIVE FINDING: the eight duration-3 World Cup fades (Rice, Saka, Guehi, O'Reilly,
   Enzo, Rogers, Watkins, Anderson) are suppressed across 38% of an 8-GW window but 100% of
   a 3-GW one. Truncating the horizon multiplies the weight of exactly the overlay calls the
   Community Shield REFUTED. A 3-GW objective doubles down on the build's known error.

CAVEATS
-------
* FDR is a proxy for what the model actually uses (Dixon-Coles expected goals for established
  clubs; FDR fallback only for the three promoted sides). The fitted sensitivity is small,
  ~4% per FDR point, at rms 0.24 pts and worst 0.50 (Tarkowski, Schade). The sensitivity
  sweep in section 4 therefore matters more than the point estimate - and at higher
  sensitivities the divergence runs TOWARD our squad (Haaland, Calvert-Lewin and Schade in;
  B.Fernandes and Joao Pedro out).
* Pool is ~45 players, not 558. Cheap MID/FWD enablers are absent, so the bench is fixed at
  the price floor and bench value sits outside the objective.

VERDICT: keep the 8-GW objective and the committed squad. If a formal horizon change is ever
wanted, 5 GWs is the defensible number - and it changes nothing.

Run: python notebooks/gw01_horizon_sensitivity.py
"""

import itertools
import math

import pulp

DECAY = 0.85
W8 = [DECAY**g for g in range(8)]
A = 0.012621  # model_share = A * mins_per_gw (notebooks/gw01_final_overlay_scale.py)

# ---- fixture grid: FDR by gameweek (research/2026-27/fixtures-gw1-8.md) -----
FDR = {
    "LIV": [3, 3, 2, 2, 3, 4, 3, 2], "CRY": [3, 4, 3, 2, 3, 3, 3, 2],
    "MUN": [2, 2, 3, 4, 3, 3, 3, 3], "NEW": [4, 3, 3, 3, 2, 2, 3, 3],
    "SUN": [2, 2, 3, 4, 5, 2, 3, 2], "ARS": [2, 4, 4, 3, 3, 2, 3, 3],
    "CHE": [3, 2, 5, 2, 3, 3, 3, 3], "COV": [5, 2, 5, 2, 3, 2, 3, 2],
    "FUL": [4, 3, 3, 4, 4, 2, 2, 2], "MCI": [3, 3, 2, 4, 2, 4, 2, 4],
    "NFO": [2, 4, 3, 4, 2, 3, 4, 2], "TOT": [3, 2, 3, 3, 3, 4, 2, 4],
    "AVL": [3, 4, 2, 3, 3, 3, 3, 4], "BRE": [3, 3, 2, 3, 4, 4, 4, 2],
    "BHA": [3, 4, 2, 2, 4, 3, 3, 4], "HUL": [4, 2, 3, 4, 3, 3, 3, 3],
    "EVE": [3, 3, 4, 3, 2, 2, 4, 5], "IPS": [2, 4, 4, 3, 3, 2, 5, 3],
    "LEE": [3, 3, 3, 2, 3, 5, 4, 3], "BOU": [5, 3, 3, 3, 4, 4, 2, 4],
}

# name, club, pos, price, pre_horizon8, mins_per_gw|None, overlay|None, dur|None, post8|None
# Rows with no mins/GW are included only where the overlay is absent, so post == pre
# exactly and nothing has to be assumed.
POOL = [
    ("Haaland", "MCI", "FWD", 15.5, 29.37, 70.4, None, None, None),
    ("B.Fernandes", "MUN", "MID", 12.0, 26.28, 72.3, 0.88, 8, None),
    ("Semenyo", "MCI", "MID", 8.5, 22.47, 76.1, None, None, None),
    ("Thiago", "BRE", "FWD", 8.0, 22.38, 76.1, 0.80, 8, None),
    ("Mbeumo", "MUN", "MID", 8.0, 20.99, 64.6, 0.85, 8, None),
    ("Enzo", "CHE", "MID", 7.0, 20.71, 72.3, 0.50, 3, None),
    ("Guehi", "MCI", "DEF", 6.0, 20.42, 72.3, 0.50, 3, None),
    ("Raya", "ARS", "GKP", 6.0, 20.35, 76.1, 0.92, 8, None),
    ("Gabriel", "ARS", "DEF", 8.0, 20.23, 62.7, None, None, None),
    ("O'Reilly", "MCI", "DEF", 6.5, 19.64, 60.8, 0.38, 3, None),
    ("Gibbs-White", "NFO", "MID", 8.0, 19.01, 72.3, 0.85, 8, None),
    ("Joao Pedro", "CHE", "FWD", 7.5, 18.98, 64.6, 0.78, 8, None),
    ("Watkins", "AVL", "FWD", 8.0, 18.77, 68.5, 0.55, 3, None),
    ("Szoboszlai", "LIV", "MID", 7.0, 18.53, 74.2, 0.85, 8, None),
    ("Rice", "ARS", "MID", 7.5, 18.40, 72.3, 0.52, 3, None),
    ("Schade", "BRE", "MID", 6.0, 18.23, 66.5, 0.72, 8, None),
    ("Saka", "ARS", "MID", 9.5, 18.11, 53.2, 0.50, 3, None),
    ("Pickford", "EVE", "GKP", 5.5, 17.95, 78.0, None, None, None),
    ("Gakpo", "LIV", "MID", 7.0, 17.78, 66.5, 0.70, 8, None),
    ("Rogers", "CHE", "MID", 7.5, 17.62, 76.1, 0.45, 3, None),
    ("Donnarumma", "MCI", "GKP", 5.5, 17.61, 70.4, None, None, None),
    ("Kelleher", "BRE", "GKP", 5.0, 17.48, 76.1, None, None, None),
    ("Virgil", "LIV", "DEF", 6.5, 17.38, 78.0, 0.85, 8, None),
    ("Wirtz", "LIV", "MID", 7.5, 16.88, 57.0, 0.80, 8, None),
    ("Anderson", "MCI", "MID", 6.5, 16.87, 76.1, 0.60, 3, None),
    ("Tavernier", "BOU", "MID", 6.0, 16.85, 64.6, None, None, None),
    ("Verbruggen", "BHA", "GKP", 4.5, 16.82, 78.0, 0.70, 2, None),
    ("Leno", "FUL", "GKP", 4.5, 16.71, 78.0, None, None, None),
    ("Henderson", "CRY", "GKP", 5.0, 16.65, 76.1, None, None, None),
    ("Petrovic", "BOU", "GKP", 4.5, 16.54, 78.0, None, None, None),
    ("Roefs", "SUN", "GKP", 5.0, 16.51, None, None, None, 16.51),
    ("Sanchez", "CHE", "GKP", 5.0, 16.44, None, None, None, 16.44),
    ("Tarkowski", "EVE", "DEF", 6.0, 16.24, None, None, None, 16.24),
    ("Calvert-Lewin", "LEE", "FWD", 6.0, 16.18, None, None, None, 16.18),
    ("Truffert", "BOU", "DEF", 5.5, 15.97, None, None, None, 15.97),
    ("Thiaw", "NEW", "DEF", 5.0, 15.72, None, None, None, 15.72),
    ("Lammens", "MUN", "GKP", 5.0, 15.68, None, None, None, 15.68),
    ("Martinez", "AVL", "GKP", 5.0, 15.27, None, None, None, 15.27),
    ("Sels", "NFO", "GKP", 5.0, 14.30, None, None, None, 14.30),
    ("Evanilson", "BOU", "FWD", 6.0, 14.12, None, None, None, 14.12),
    ("Cash", "AVL", "DEF", 4.5, 13.53, None, None, None, 13.53),
    ("Hume", "SUN", "DEF", 4.5, 13.44, None, None, None, 13.44),
    ("Vicario", "TOT", "GKP", 4.5, 12.87, None, None, None, 12.87),
    ("Bogle", "LEE", "DEF", 4.5, 12.70, None, None, None, 12.70),
    ("Igor Jesus", "NFO", "FWD", 6.0, 12.53, None, None, None, 12.53),
]

# Bournemouth ban: worst opening run in the league (standing fixture rule, memo iteration 2).
BANNED = {"Truffert", "Petrovic", "Tavernier", "Evanilson"}

# Committed GW1 xPts for the owned XI (decisions/gw01_solve.json) - the fit targets.
OWNED_GW1 = {
    "Raya": 3.99, "Gabriel": 4.24, "Tarkowski": 3.87, "Thiaw": 3.03, "Semenyo": 4.78,
    "Mbeumo": 4.88, "Wirtz": 3.76, "Szoboszlai": 3.38, "Schade": 3.62, "Haaland": 6.32,
    "Calvert-Lewin": 3.22,
}
OUR_XI = set(OWNED_GW1)
BENCH_FLOOR = {"GKP": 4.0, "DEF": 4.0, "MID": 4.5, "FWD": 4.5}
SQUAD = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
BY_NAME = {p[0]: p for p in POOL}


def _shares(overlay, dur, model_share, n):
    """Per-GW start share. An overlay applies only across its duration_gws."""
    if overlay is None:
        return [1.0] * n
    return [overlay / model_share if g < dur else 1.0 for g in range(n)]


def per_gw(p, k):
    """Post-overlay xPts for gameweeks 1..8."""
    _name, club, _pos, _price, pre8, mins, overlay, dur, post8 = p
    mult = [math.exp(-k * (f - 3)) for f in FDR[club][:8]]
    base = pre8 / sum(W8[g] * mult[g] for g in range(8))
    model_share = A * mins if mins else None
    shares = _shares(overlay, dur, model_share, 8)
    series = [base * mult[g] * shares[g] for g in range(8)]
    if post8 is not None:  # honour a known post-overlay total exactly
        scale = post8 / sum(W8[g] * series[g] for g in range(8))
        series = [x * scale for x in series]
    return series


def fit_k():
    """Least-squares fixture sensitivity against the committed GW1 column."""
    def sse(k):
        return sum((per_gw(BY_NAME[n], k)[0] - gw1) ** 2 for n, gw1 in OWNED_GW1.items())
    k = min((sse(i / 2000.0), i / 2000.0) for i in range(601))[1]
    return k, sse(k)


def solve(k, n, decay=DECAY):
    """Best starting XI over an n-GW decayed window, bench held at the price floor.

    Captaincy enters as one extra doubled GW1 term, because the armband is part of the
    decision and an XI-only objective without it systematically ejects Haaland on price.
    """
    weights = [decay**g for g in range(n)]
    cand = [p for p in POOL if p[0] not in BANNED]
    series = {p[0]: per_gw(p, k) for p in cand}
    best = None
    for n_def, n_mid, n_fwd in itertools.product(range(3, 6), range(2, 6), range(1, 4)):
        if 1 + n_def + n_mid + n_fwd != 11:
            continue
        xi = {"GKP": 1, "DEF": n_def, "MID": n_mid, "FWD": n_fwd}
        bench = {pos: SQUAD[pos] - xi[pos] for pos in SQUAD}
        if any(v < 0 for v in bench.values()) or sum(bench.values()) != 4:
            continue
        budget = 100.0 - sum(BENCH_FLOOR[pos] * cnt for pos, cnt in bench.items())
        prob = pulp.LpProblem("xi", pulp.LpMaximize)
        pick = {p[0]: pulp.LpVariable(f"p_{p[0]}", cat="Binary") for p in cand}
        arm = {p[0]: pulp.LpVariable(f"c_{p[0]}", cat="Binary") for p in cand}
        prob += pulp.lpSum(
            sum(weights[i] * series[p[0]][i] for i in range(n)) * pick[p[0]]
            + series[p[0]][0] * arm[p[0]]
            for p in cand
        )
        prob += pulp.lpSum(p[3] * pick[p[0]] for p in cand) <= budget
        prob += pulp.lpSum(arm.values()) == 1
        for p in cand:
            prob += arm[p[0]] <= pick[p[0]]
        for pos, cnt in xi.items():
            prob += pulp.lpSum(pick[p[0]] for p in cand if p[2] == pos) == cnt
        for club in {p[1] for p in cand}:
            prob += pulp.lpSum(pick[p[0]] for p in cand if p[1] == club) <= 3
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[prob.status] != "Optimal":
            continue
        value = pulp.value(prob.objective)
        if best is None or value > best[0]:
            best = (
                value,
                f"{n_def}-{n_mid}-{n_fwd}",
                {p[0] for p in cand if pick[p[0]].value() > 0.5},
                next((p[0] for p in cand if arm[p[0]].value() and arm[p[0]].value() > 0.5), "-"),
            )
    return best


def _diff(xi):
    if xi == OUR_XI:
        return "identical to ours"
    return ("in: " + ",".join(sorted(xi - OUR_XI))
            + " | out: " + ",".join(sorted(OUR_XI - xi)))


def main() -> None:
    print("1. HOW FRONT-LOADED IS THE CURRENT OBJECTIVE ALREADY?")
    total = sum(W8)
    for n in range(1, 6):
        print(f"   GW1-{n} carries {sum(W8[:n]) / total * 100:5.1f}% of the 8-GW objective")

    k, sse = fit_k()
    rms = (sse / len(OWNED_GW1)) ** 0.5
    worst = max((abs(per_gw(BY_NAME[n], k)[0] - g), n) for n, g in OWNED_GW1.items())
    print()
    print(f"2. FITTED FIXTURE SENSITIVITY  K = {k:.4f}"
          f"  ({(math.exp(k) - 1) * 100:.1f}% per FDR point)")
    print(f"   rms {rms:.2f} pts against the committed GW1 column;"
          f" worst {worst[0]:.2f} ({worst[1]})")

    print()
    print("3. OPTIMAL XI AS THE OBJECTIVE IS FRONT-LOADED (captaincy included)")
    print(f"   {'objective':<26}{'shape':<8}{'captain':<14}{'match':<8}differences vs our XI")
    for label, decay, n in (
        ("8 GW, decay 0.85 (current)", 0.85, 8), ("8 GW, decay 0.80", 0.80, 8),
        ("8 GW, decay 0.75", 0.75, 8), ("8 GW, decay 0.70", 0.70, 8),
        ("5 GW, decay 0.85", 0.85, 5), ("3 GW, decay 0.85", 0.85, 3),
        ("3 GW, flat", 1.00, 3), ("1 GW only", 1.00, 1),
    ):
        _v, shape, xi, armband = solve(k, n, decay)
        match = f"{11 - len(xi - OUR_XI)}/11"
        print(f"   {label:<26}{shape:<8}{armband:<14}{match:<8}{_diff(xi)}")

    print()
    print("4. ROBUSTNESS - is the 3-vs-8 verdict sensitive to K?")
    for k_try in (k, 0.08, 0.15, 0.25, 0.40):
        x8 = solve(k_try, 8)[2]
        x3 = solve(k_try, 3)[2]
        moved = x3 ^ x8
        detail = ("identical XI" if not moved else
                  "in: " + ",".join(sorted(x3 - x8)) + " | out: " + ",".join(sorted(x8 - x3)))
        print(f"   K={k_try:.3f} ({(math.exp(k_try) - 1) * 100:4.1f}%/pt): {detail}")

    print()
    print("5. THE DECISIVE EFFECT - duration-3 World Cup fades FILL a 3-GW window")
    print(f"   {'player':<14}{'overlay':>8}{'dur':>5}{'8-GW':>8}{'3-GW':>8}")
    for p in POOL:
        if p[6] is not None and p[7] is not None and p[7] <= 3:
            print(f"   {p[0]:<14}{p[6]:>8.2f}{p[7]:>5}"
                  f"{p[7] / 8 * 100:>7.0f}%{min(p[7], 3) / 3 * 100:>7.0f}%")
    print()
    print("   Shortening the horizon multiplies the weight of exactly the overlay calls the")
    print("   Community Shield refuted (Rice, Saka, Guehi and O'Reilly all now start).")
    print()
    print("VERDICT: keep the 8-GW objective. 5 GWs is the only defensible alternative, and")
    print("it reproduces the committed XI exactly.")


if __name__ == "__main__":
    main()

"""Phase 2 — models (see PLAN.md §4).

Build order (order = importance):
  minutes.py    P(start)/P(60+)/P(cameo) — LightGBM on vaastav history + flags/congestion
  team_dc.py    Dixon-Coles team strength (penaltyblog) blended with odds signal
  xpts.py       per-player expected points per GW; 8-GW horizon with decay

Gate: point-in-time backtests on 2023/24–2025/26 must beat template baseline
in full-season simulation before anything here feeds a decision memo.
"""

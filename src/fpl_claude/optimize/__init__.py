"""Phase 3 — MILP squad optimizer.

milp.py: PuLP + HiGHS following the open-fpl-solver formulation — squad/XI/captain/
vice/bench-order/transfers/chips over a rolling 8-GW horizon; objective = decayed
xPts − 4×hits. Constraints come exclusively from rules.engine.Ruleset; the optimizer
must refuse to run while the ruleset has unverified sections (unless overridden).
"""

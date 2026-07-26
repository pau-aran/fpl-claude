"""Phase 2 — models. Build-vs-extract split (decided Jul 2026):

  minutes.py      BUILT — our edge; heuristic v1, LightGBM upgrade later,
                  news-overlay hook is the whole point
  team.py         EXTRACTED — penaltyblog Dixon-Coles + FDR fallback
  rates.py        per-90 event rates from FPL data, prior-blended
  xpts.py         BUILT — rules-YAML-driven scoring map (never hard-coded)
  projections.py  glue: per-GW xPts over the decayed horizon + CLI

Gate: point-in-time backtests on 2023/24–2025/26 must beat template baseline
in full-season simulation before anything here feeds a decision memo.
"""

# NOTE: projections is not imported here so `python -m fpl_claude.models.projections`
# runs without runpy's double-import warning; import it directly where needed.
from . import minutes, rates, team, xpts  # noqa: F401

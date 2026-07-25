"""Baseline GW1 solve — the model's naive proposal, BEFORE any manager overlay."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, r"C:\Users\pau_8\Documents\fpl-claude\src")
from fpl_claude.optimize.milp import optimize  # noqa: E402
from fpl_claude.rules.engine import Ruleset  # noqa: E402

df = pd.read_csv(r"C:\Users\pau_8\Documents\fpl-claude\db\projections\2026-07-25.csv")
rules = Ruleset.load("2026-27")
print("ruleset verified:", rules.is_verified())

res = optimize(df, rules=rules)
sq = df[df["id"].isin(res.squad)].copy()
sq["role"] = "bench"
sq.loc[sq["id"].isin(res.xi), "role"] = "XI"
sq.loc[sq["id"] == res.captain, "role"] = "C"
sq.loc[sq["id"] == res.vice, "role"] = "V"
order = {"C": 0, "V": 1, "XI": 2, "bench": 3}
posn = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
sq["_o"] = sq["role"].map(order)
sq["_p"] = sq["position"].map(posn)
sq = sq.sort_values(["_o", "_p", "price"], ascending=[True, True, False])

cols = ["web_name", "team", "position", "price", "xpts_gw1", "xpts_horizon",
        "ownership_pct", "minutes_confidence", "role"]
out = Path(__file__).parent / "solve_baseline.md"
lines = ["# Baseline GW1 solve (NO manager overlay — model proposal only)\n"]
lines.append(f"- objective: {res.objective}")
lines.append(f"- spend: {sq['price'].sum():.1f}  bank: {100 - sq['price'].sum():.1f}")
lines.append(f"- captain id {res.captain}, vice id {res.vice}\n")
lines.append(sq[cols].to_markdown(index=False))
lines.append("\n## Club concentration\n")
lines.append(sq["team"].value_counts().to_markdown())
lines.append("\n## Minutes confidence in squad\n")
lines.append(sq["minutes_confidence"].value_counts().to_markdown())
out.write_text("\n".join(lines), encoding="utf-8")
print(f"written {out}")

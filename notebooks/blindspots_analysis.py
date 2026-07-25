"""Which players will the minutes model be BLIND on at the season open?

minutes._start_share falls back to NEUTRAL_START_SHARE=0.5 when there is no prior
(team_games==0 pre-season). A player with no 2025/26 row therefore projects as a
coin-flip starter regardless of whether he is nailed or a squad filler. Those are
the rows the manager overlay must hand-write.

Also flags the opposite error: players WITH a prior who changed club, where last
season's start share is attached to a different competitive context.
"""
import csv
import json
from pathlib import Path

ROOT = Path(r"C:\Users\pau_8\Documents\fpl-claude")
bs = json.loads((ROOT / "db" / "raw" / "2026-07-25" / "bootstrap.json").read_text(encoding="utf-8"))
short = {t["id"]: t["short_name"] for t in bs["teams"]}
POS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

prior = {}
with (ROOT / "db" / "vaastav" / "2025-26" / "players_raw.csv").open(encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        prior[int(row["code"])] = row

lines = ["# Minutes-model blind spots at the 2026/27 season open\n"]
lines.append(
    "`minutes._start_share` returns NEUTRAL_START_SHARE=0.5 when a player has no prior-season\n"
    "row. Pre-season `team_games` is 0 for everyone, so **every player below is projected as a\n"
    "50/50 starter** — nailed £9m signings and 19-year-old squad fillers alike. These are the\n"
    "rows where a hand-written overlay is worth the most.\n"
)

no_prior, moved, kept = [], [], []
for e in bs["elements"]:
    row = prior.get(int(e["code"]))
    rec = (e, row)
    if row is None:
        no_prior.append(rec)
    else:
        # vaastav team column is last season's club name; compare via starts context
        moved.append(rec) if (e.get("team_join_date") or "") >= "2026-06-01" else kept.append(rec)

lines.append(f"\n## No prior row at all — projected 0.5 by default ({len(no_prior)} players)\n")
lines.append("Ranked by price. Anything above ~£5.5m here is a squad-selection-relevant blind spot.\n")
lines.append("| Player | Club | Pos | Price | Own% | Joined | Status |")
lines.append("|---|---|---|---|---|---|---|")
for e, _ in sorted(no_prior, key=lambda r: -r[0]["now_cost"])[:45]:
    lines.append(
        f"| {e['web_name']} | {short[e['team']]} | {POS[e['element_type']]} | {e['now_cost']/10:.1f} "
        f"| {e['selected_by_percent']} | {e.get('team_join_date') or '-'} | {e['status']} |"
    )

lines.append(
    f"\n## Has a prior BUT changed club this summer ({len(moved)} players)\n\n"
    "Last season's start share is carried into a **different** competitive context — a nailed\n"
    "starter at a mid-table club is not a nailed starter at a title contender, and vice versa.\n"
    "The model will be confidently wrong here rather than merely uncertain.\n"
)
lines.append("| Player | New club | Pos | Price | Own% | 25/26 starts | 25/26 mins |")
lines.append("|---|---|---|---|---|---|---|")
for e, row in sorted(moved, key=lambda r: -r[0]["now_cost"])[:40]:
    lines.append(
        f"| {e['web_name']} | {short[e['team']]} | {POS[e['element_type']]} | {e['now_cost']/10:.1f} "
        f"| {e['selected_by_percent']} | {row.get('starts','?')} | {row.get('minutes','?')} |"
    )

# per-club blindness: promoted sides should be near-total
lines.append("\n## Blindness by club (share of squad with no prior row)\n")
lines.append("| Club | No prior | Squad | % blind |")
lines.append("|---|---|---|---|")
by_club = {}
for e in bs["elements"]:
    c = short[e["team"]]
    tot, blind = by_club.get(c, (0, 0))
    by_club[c] = (tot + 1, blind + (1 if int(e["code"]) not in prior else 0))
for c, (tot, blind) in sorted(by_club.items(), key=lambda kv: -kv[1][1] / kv[1][0]):
    lines.append(f"| {c} | {blind} | {tot} | {100*blind/tot:.0f}% |")

out = Path(__file__).parent / "blindspots.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"written {out}: {len(no_prior)} no-prior, {len(moved)} moved-with-prior, {len(kept)} stable")

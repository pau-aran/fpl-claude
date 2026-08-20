"""GW1 overlay, iteration 3 — the T-24h revision on a 5-gameweek horizon.

Iterations 1-2 were written on 2026-07-26, twenty-six days out, and said so:
"it will be re-solved at T-48h against actual team news", with the Arsenal calls
explicitly gated on the Community Shield of 16 August. That match has now been
played and the pre-deadline predicted line-ups are out, so this iteration keeps
every call the evidence supports, MOVES the ones it contradicts, and adds the
players the July sweep had no reason to name.

It starts from `decisions/overlays/gw01.json` rather than replacing it: the
World Cup thesis is unchanged (rest ended ~10-12 August, so the deep runners
still reach this deadline on ~10 days of club training), and an overlay entry
that new evidence does not touch should not be silently rewritten.

Durations are unchanged in spirit but now read against a FIVE-gameweek horizon:
a `duration_gws: 3` fatigue call fades GW1-3 and lets GW4-5 project clean.

Sources are named per entry. All team-news evidence here is second-hand — the
FPL API and every FPL news domain are egress-blocked in this sandbox, so it
comes through web search summaries, and each claim was cross-checked against the
snapshot's own squad lists before it was written down (that check is what caught
a summarised Arsenal XI naming a midfielder who is not in the squad, and a Leeds
keeper who is on another club's roster in this payload).

CLI:  python notebooks/build_overlay_gw01_it3.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "decisions" / "overlays" / "gw01.json"
OUT = ROOT / "decisions" / "overlays" / "gw01-it3.json"
SNAPSHOT = ROOT / "db" / "raw" / "2026-08-20" / "bootstrap.json"

# player id -> (start_share, duration_gws, reason). Ids are 2026/27 element ids,
# stable within a season and verified against the snapshot below before writing.
REVISIONS: dict[int, tuple[float, int, str]] = {
    # ---------- COMMUNITY SHIELD, 16 Aug (ARS v MCI): the gate the memo set ----------
    13: (0.40, 3, (
        "Declan Rice (ARS MID, £7.5m, 22.3%) — FADED HARDER, not softened. "
        "The memo gated Arsenal's World Cup calls on the Community Shield and "
        "he did NOT start it (Lewis-Skelly partnered in midfield). Reported "
        "nerve pain on top of the England semi-final load, with a single "
        "pre-season run-out of no more than 45 minutes. 0.52 -> 0.40."
    )),
    12: (0.40, 3, (
        "Bukayo Saka (ARS MID, £9.5m, 10.6%) — did not start the Community "
        "Shield; came on for about 30 minutes, and is managing an Achilles "
        "problem. At £9.5m we are paying for 90 minutes against Coventry, "
        "which is exactly what the evidence says we will not get. 0.50 -> 0.40."
    )),
    25: (0.55, 3, (
        "Viktor Gyökeres (ARS FWD, £7.5m, 13.0%) — NEW EVIDENCE, big move down. "
        "Havertz started the Community Shield as Arsenal's nine and Gyökeres "
        "did not. The July overlay had him at 0.78 on the assumption he was "
        "the undisputed starter; one competitive match says otherwise. 0.78 -> 0.55."
    )),
    26: (0.72, 3, (
        "Kai Havertz (ARS FWD, £7.5m, 4.0%) — the other side of the Gyökeres "
        "call: he STARTED the Community Shield at centre-forward. Not raised "
        "further because a 4%-owned £7.5m forward on one start is thin evidence, "
        "and his own prior is thin too (577 minutes last season — defect D2's "
        "class of player). NEW entry."
    )),
    11: (0.82, 5, (
        "Cristhian Mosquera (ARS DEF, £5.5m, 16.9%) — started the Community "
        "Shield at centre-back, and Arsenal's centre-back room is thin behind "
        "him: Saliba is out 4-5 months and Timber carries a groin injury FPL "
        "dates to deadline day. Fixture GW1 is Coventry at home, the softest on "
        "the slate. NEW entry."
    )),
    8: (0.80, 5, (
        "Riccardo Calafiori (ARS DEF, £5.5m, 15.3%) — started the Community "
        "Shield at left-back. Italy did not reach the World Cup semi-finals, so "
        "he is not in the late-returner cohort at all. NEW entry."
    )),
    10: (0.70, 5, (
        "Ben White (ARS DEF, £5.5m, 0.2%) — STATE.md called his flag 'the "
        "highest-value single unknown' in the game. It is resolved: he is "
        "status 'a' in this snapshot and he started the Community Shield at "
        "right-back. Held at 0.70 rather than higher because Timber returning "
        "takes the shirt back. NEW entry."
    )),
    388: (0.30, 3, (
        "Marc Guéhi (MCI DEF, £6.0m, 24.0%) — the single largest correction in "
        "this iteration, and it goes AGAINST our own model, which ranks him the "
        "best defender in the game over five gameweeks. He did not start the "
        "Community Shield: Maresca picked Khusanov, Rúben Dias and Gvardiol. "
        "Reported as 'far from a certainty to start' with no full pre-season. "
        "Nearly a quarter of the game owns him. 0.50 -> 0.30."
    )),
    387: (0.60, 3, (
        "Nico O'Reilly (MCI DEF, £6.5m, 22.9%) — RAISED on evidence that cuts "
        "against the July call. He started the Community Shield (his first "
        "post-World Cup start, kept to about an hour by design), so the minutes "
        "fade was too harsh. The STRUCTURAL objection stands and is untouched by "
        "this: he is playing a deeper role than under Guardiola, so the attacking "
        "returns a £6.5m defender's price implies are still the ones the system "
        "suppresses. That objection lives in the rates, not the minutes, which is "
        "why we raise the share and still do not buy him. 0.38 -> 0.60."
    )),
    391: (0.85, 5, (
        "Joško Gvardiol (MCI DEF, £5.5m, 10.7%) — started the Community Shield "
        "and is the City defender the evidence actually points at: a pound "
        "cheaper than Guéhi and O'Reilly, and one of the two centre-backs "
        "Maresca trusted in his first competitive selection. NEW entry."
    )),
    481: (0.85, 3, (
        "Elliot Anderson (MCI MID, £6.5m, 11.8%) — started the Community Shield "
        "in central midfield alongside Kovačić, which is what the £116m "
        "British-record fee always implied. The July entry already faded him "
        "least of the City cohort; the Shield converts that read into evidence. "
        "0.60 -> 0.85."
    )),
    399: (0.40, 3, (
        "Rayan Cherki (MCI MID, £7.5m, 9.4%) — did not start the Community "
        "Shield (Foden and Doku were the wide picks). France's third-place "
        "play-off cohort plus a new manager who has now shown his hand. "
        "0.45 -> 0.40."
    )),
    400: (0.00, 2, (
        "Jérémy Doku (MCI MID, £7.5m, 6.4%) — OUT. Sustained a calf injury "
        "against Arsenal in the Community Shield and is reported to miss City's "
        "opener at home to Bournemouth. He carries NO FPL flag in this snapshot "
        "(status 'a'), so this is precisely the invisible-risk class the overlay "
        "exists for. Scoped to 2 gameweeks, not the horizon: a calf strain is "
        "not a season, and pricing a transient as permanent is the overlay-horizon "
        "defect we already paid for once. NEW entry."
    )),

    # ---------- PRE-DEADLINE PREDICTED LINE-UPS ----------
    200: (0.80, 5, (
        "Maxence Lacroix (CHE DEF, £6.0m, 12.0%) — the July entry set him to "
        "0.15 because Chelsea had agreed a fee and 12.9% of the game was holding "
        "an asset about to be repriced at another club. THE MOVE HAS COMPLETED: "
        "he is a Chelsea player at £6.0m in this snapshot and sits in Chelsea's "
        "predicted back three. Leaving 0.15 in place would fade a likely starter "
        "on a fact that has expired. 0.15 -> 0.80."
    )),
    155: (0.42, 3, (
        "Enzo Fernández (CHE MID, £7.0m, 5.4%) — NOT in Chelsea's predicted XI; "
        "Lavia and Caicedo are the two. Argentina runner-up, so the deepest "
        "fatigue cohort, and his late return is reported as delaying his "
        "involvement. 0.50 -> 0.42."
    )),
    40: (0.55, 3, (
        "Morgan Rogers (CHE MID, £7.5m, 30.7%) — SOURCES CONFLICT and the entry "
        "records the conflict rather than picking a winner: one pre-deadline read "
        "has his Gameweek 1 minutes 'in serious doubt' with no full pre-season, "
        "another starts him in Chelsea's predicted XI. Split to the midpoint. "
        "The three-count case against him (England semi-finalist, four-day-old "
        "£117m signing, takes no Chelsea set pieces) is unchanged. 0.45 -> 0.55."
    )),
    31: (0.75, 3, (
        "Ezri Konsa (AVL DEF, £4.5m, 17.4%) — in Villa's predicted back four. "
        "The England semi-final load is real but he is a £4.5m enabler whose "
        "whole case is that he plays, and the line-up evidence says he plays. "
        "0.50 -> 0.75."
    )),
    55: (0.78, 3, (
        "Ollie Watkins (AVL FWD, £8.0m, 12.4%) — in Villa's predicted XI as the "
        "nine. The July fade was already the mildest on the board ('a slight "
        "doubt'); the line-up resolves it. 0.55 -> 0.78."
    )),
    379: (0.85, 5, (
        "Alexander Isak (LIV FWD, £9.0m, 11.3%) — RAISED, and the most important "
        "MODEL correction in the file. He is Liverpool's predicted starting nine "
        "and FPL's listed penalty taker, and our raw table projects him at 6.83 "
        "points over eight gameweeks — bottom-of-the-squad numbers for a £9.0m "
        "striker — purely because his prior is 694 minutes and 8 starts from an "
        "injury-shortened first Liverpool season. That is defect D2 exactly: the "
        "minutes prior cannot tell 'was benched' from 'was injured'. The overlay "
        "fixes the minutes; it does NOT fix his per-90 rates, which are still "
        "blended off that thin sample, so he stays under-rated even here and we "
        "do not treat his projection as decision-grade. 0.78 -> 0.85."
    )),
    439: (0.28, 2, (
        "Benjamin Šeško (MUN FWD, £7.0m, 2.8%) — shin injury, FPL 75%, and not "
        "in United's predicted XI (Mbeumo leads the line). RE-SCOPED from 8 "
        "gameweeks to 2: the flag was recorded weeks before the deadline and "
        "defect D1 prices every flag as a horizon-long absence. 0.30/8 -> 0.28/2."
    )),
    430: (0.00, 2, (
        "Mason Mount (MUN MID, £5.5m, 0.1%) — OUT: foot knock taken against PSG "
        "in pre-season, reported to have missed training and to be unfit for the "
        "opener, with Tielemans in line to replace him. Carries no FPL flag. "
        "Negligible ownership; written down anyway because an unflagged absence "
        "is the exact evidence class this file is for. NEW entry."
    )),
}


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    teams = {t["id"]: t["short_name"] for t in snapshot["teams"]}
    by_id = {int(e["id"]): e for e in snapshot["elements"]}

    missing = [pid for pid in REVISIONS if pid not in by_id]
    if missing:
        raise SystemExit(f"revision ids absent from the snapshot: {missing}")

    out = dict(base)
    changed, added = 0, 0
    for pid, (share, duration, reason) in REVISIONS.items():
        element = by_id[pid]
        key = str(pid)
        if key in out:
            changed += 1
        else:
            added += 1
        out[key] = {
            "start_share": share,
            "duration_gws": duration,
            "reason": reason,
            "_player": (
                f"{element['web_name']} ({teams[element['team']]}, "
                f"{element['now_cost'] / 10})"
            ),
        }

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"overlay written: {OUT}")
    print(f"  {len(base)} base entries -> {len(out)} ({changed} revised, {added} new)")
    for pid, (share, _, _) in sorted(REVISIONS.items()):
        old = base.get(str(pid), {}).get("start_share")
        arrow = f"{old} -> {share}" if old is not None else f"NEW {share}"
        print(f"  {by_id[pid]['web_name']:16s} {teams[by_id[pid]['team']]:4s} {arrow}")


if __name__ == "__main__":
    main()

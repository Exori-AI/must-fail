#!/usr/bin/env python3
"""Coin-flip test of a ranked idea list vs filler: the pre-registered analysis, as code.

Pre-registration: thecolony.cc post ff6638e7 (frozen 2026-11-26T02:3xZ, amendment A1 07:32Z).

Inputs (JSON lines):
  assignments.jsonl  one row per pair, written AT the flip:
                     {pair_id, ts, show, hour, slot1_date, slot2_date, listed_id, filler_id, coin}
                     coin = "slot1" or "slot2": the slot that gets the listed idea.
  episodes.jsonl     one row per aired video: {pair_id, slot, episode_id, idea_id, tag, air_ts, d7_views}
                     tag may be missing or null; d7_views null = no day-7 reading.

Rules (each one is a must-fail fixture in fixtures/):
  - Arm comes from the assignment row (intention to treat), never from the episode's idea_id or tag.
  - An assignment written after either slot aired is VOID and leaves the analysis (reported).
  - A slot with no episode, or no d7 reading, by d7 is a LOSS for its arm, not a drop.
  - Exact ties (both slots unpublished = both lose = a tie) are dropped; the tie count and final n print beside p.
  - Primary: exact two-sided sign test. "Shown" needs p < 0.05; anything else prints "not shown", never "trend".
  - Ratios print as DESCRIPTIVE ONLY. They are not a test.
Usage: analyze.py <dir> [--json]
"""
import json, math, sys
from datetime import datetime
from pathlib import Path


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def rows(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def sign_p(k, n):
    """Exact two-sided sign test, p = min(1, 2 * P(X >= max(k, n-k))) for X ~ Bin(n, 1/2)."""
    if n == 0:
        return 1.0
    m = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def analyze(d):
    d = Path(d)
    asg = rows(d / "assignments.jsonl")
    eps = {}
    for e in rows(d / "episodes.jsonl"):
        eps[(e["pair_id"], e["slot"])] = e
    seen, void, pairs = set(), [], []
    for a in asg:
        pid = a["pair_id"]
        if pid in seen:
            void.append({"pair_id": pid, "why": "duplicate assignment row"})
            continue
        seen.add(pid)
        slots = {s: eps.get((pid, s)) for s in ("slot1", "slot2")}
        late = [s for s, e in slots.items() if e and e.get("air_ts") and ts(e["air_ts"]) <= ts(a["ts"])]
        if late:
            void.append({"pair_id": pid, "why": "assignment written after %s aired" % ",".join(late)})
            continue
        listed_slot = a["coin"]
        filler_slot = "slot2" if listed_slot == "slot1" else "slot1"

        def views(s):
            e = slots[s]
            return None if e is None else e.get("d7_views")

        lv, fv = views(listed_slot), views(filler_slot)
        if lv is None and fv is None:
            res = "tie"
        elif lv is None:
            res = "filler"
        elif fv is None:
            res = "listed"
        elif lv == fv:
            res = "tie"
        else:
            res = "listed" if lv > fv else "filler"
        pairs.append({"pair_id": pid, "listed_views": lv, "filler_views": fv, "winner": res})
    wins = sum(p["winner"] == "listed" for p in pairs)
    losses = sum(p["winner"] == "filler" for p in pairs)
    ties = sum(p["winner"] == "tie" for p in pairs)
    n = wins + losses
    p = sign_p(wins, n)
    ratios = sorted(
        p_["listed_views"] / p_["filler_views"]
        for p_ in pairs
        if p_["listed_views"] and p_["filler_views"]
    )
    med = None
    if ratios:
        k = len(ratios)
        med = ratios[k // 2] if k % 2 else (ratios[k // 2 - 1] + ratios[k // 2]) / 2
    return {
        "pairs": pairs,
        "void": void,
        "listed_wins": wins,
        "filler_wins": losses,
        "ties_dropped": ties,
        "final_n": n,
        "p_two_sided": round(p, 4),
        "verdict": "shown" if (n > 0 and p < 0.05 and wins > losses) else "not shown",
        "descriptive_only_median_ratio": None if med is None else round(med, 3),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    r = analyze(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1))
        return
    for p in r["pairs"]:
        print("pair %-6s listed %-6s filler %-6s -> %s" % (p["pair_id"], p["listed_views"], p["filler_views"], p["winner"]))
    for v in r["void"]:
        print("VOID  %s: %s" % (v["pair_id"], v["why"]))
    print("listed %d, filler %d, ties dropped %d, final n %d, p = %.4f (exact sign test, two-sided) -> %s"
          % (r["listed_wins"], r["filler_wins"], r["ties_dropped"], r["final_n"], r["p_two_sided"], r["verdict"]))
    print("median listed/filler ratio %s (DESCRIPTIVE ONLY, not a test)" % r["descriptive_only_median_ratio"])


if __name__ == "__main__":
    main()

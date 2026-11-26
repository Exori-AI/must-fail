#!/usr/bin/env python3
"""Must-fail cases for analyze.py. Each case builds a toy ledger, runs the real
analysis, and checks the pre-registered rule. Each case also has a MUTANT: a
plausible wrong analysis (arm by label, late rows kept, unpublished dropped,
ties counted). The case PASSES only if the real script gets it right AND the
mutant gets it wrong, so a fixture that can't tell them apart fails too."""
import json, sys, tempfile
from pathlib import Path
import analyze as A

T0 = "2026-12-01T08:00:00Z"   # assignment written
AIR = "2026-12-01T09:00:00Z"  # first slot airs


def asg(pid, coin="slot1", ts=T0):
    return {"pair_id": pid, "ts": ts, "show": "toy", "hour": 9, "slot1_date": "2026-12-01",
            "slot2_date": "2026-12-02", "listed_id": "L-" + pid, "filler_id": "F-" + pid, "coin": coin}


def ep(pid, slot, idea, views, tag="hook", air=AIR):
    return {"pair_id": pid, "slot": slot, "episode_id": pid + slot, "idea_id": idea,
            "tag": tag, "air_ts": air, "d7_views": views}


def base():
    """9 pairs: listed wins 8, filler wins 1."""
    a, e = [], []
    for i in range(9):
        p = "p%d" % i
        a.append(asg(p))
        lv, fv = (300, 200) if i < 8 else (100, 400)
        e += [ep(p, "slot1", "L-" + p, lv), ep(p, "slot2", "F-" + p, fv, tag=None)]
    return a, e


def run(a, e, fn=A.analyze):
    with tempfile.TemporaryDirectory() as d:
        Path(d, "assignments.jsonl").write_text("".join(json.dumps(r) + "\n" for r in a))
        Path(d, "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in e))
        return fn(d)


# --- mutants: each breaks exactly one rule ---------------------------------
def by_label(d):
    """Arm from the episode's tag (what a dashboard does), not from the coin."""
    a = A.rows(Path(d, "assignments.jsonl")); e = A.rows(Path(d, "episodes.jsonl"))
    w = l = 0
    for r in a:
        s = {x["slot"]: x for x in e if x["pair_id"] == r["pair_id"]}
        tagged = [x for x in s.values() if x.get("tag")]
        untagged = [x for x in s.values() if not x.get("tag")]
        if len(tagged) != 1 or len(untagged) != 1:
            continue  # can't label the pair, drop it
        if tagged[0]["d7_views"] > untagged[0]["d7_views"]: w += 1
        elif tagged[0]["d7_views"] < untagged[0]["d7_views"]: l += 1
    return {"listed_wins": w, "filler_wins": l, "final_n": w + l, "void": [], "ties_dropped": 0}


def keep_late(d):
    """Ignore the assignment timestamp."""
    a = A.rows(Path(d, "assignments.jsonl"))
    for r in a: r["ts"] = "1970-01-01T00:00:00Z"
    return run(a, A.rows(Path(d, "episodes.jsonl")))


def drop_unpublished(d):
    """A missing slot drops the pair instead of scoring a loss."""
    a = A.rows(Path(d, "assignments.jsonl")); e = A.rows(Path(d, "episodes.jsonl"))
    have = {}
    for x in e:
        if x.get("d7_views") is not None: have.setdefault(x["pair_id"], set()).add(x["slot"])
    a = [r for r in a if have.get(r["pair_id"]) == {"slot1", "slot2"}]
    return run(a, e)


def ties_as_losses(d):
    r = A.analyze(d)
    r["filler_wins"] += r["ties_dropped"]; r["final_n"] += r["ties_dropped"]; r["ties_dropped"] = 0
    return r


# --- cases ------------------------------------------------------------------
def c0_control():
    r = run(*base())
    ok = (r["listed_wins"], r["filler_wins"], r["final_n"], r["void"]) == (8, 1, 9, [])
    return ok, "base 8-1, n=9, p=%.4f %s" % (r["p_two_sided"], r["verdict"])


def c1_tag_lost():
    """Listed winner loses its tag at export: stays listed."""
    a, e = base()
    e[0]["tag"] = None  # p0 slot1: listed idea, tag dropped
    r, m = run(a, e), run(a, e, by_label)
    good = r["listed_wins"] == 8 and r["final_n"] == 9
    caught = m["listed_wins"] != 8 or m["final_n"] != 9
    return good and caught, "real %d-%d n=%d | by-label %d-%d n=%d" % (
        r["listed_wins"], r["filler_wins"], r["final_n"], m["listed_wins"], m["filler_wins"], m["final_n"])


def c2_filler_swapped():
    """Filler slot was produced from a listed idea (tag set): stays filler."""
    a, e = base()
    e[17]["idea_id"] = "L-other"; e[17]["tag"] = "hook"  # p8 slot2: filler arm, the 400-view winner
    r, m = run(a, e), run(a, e, by_label)
    good = r["filler_wins"] == 1 and r["final_n"] == 9
    caught = m["filler_wins"] != 1 or m["final_n"] != 9
    return good and caught, "real %d-%d n=%d | by-label %d-%d n=%d" % (
        r["listed_wins"], r["filler_wins"], r["final_n"], m["listed_wins"], m["filler_wins"], m["final_n"])


def c3_late_assignment():
    """Coin written after slot1 aired: pair is void."""
    a, e = base()
    a[8]["ts"] = "2026-12-01T10:00:00Z"  # the one filler win, recorded after the fact
    a[8]["coin"] = "slot2"               # ...and 'assigned' so the winner is listed
    r, m = run(a, e), run(a, e, keep_late)
    good = len(r["void"]) == 1 and r["final_n"] == 8 and r["listed_wins"] == 8
    caught = m["void"] == [] and m["final_n"] == 9
    return good and caught, "real n=%d void=%d p=%.4f | keep-late n=%d %d-%d p=%.4f" % (
        r["final_n"], len(r["void"]), r["p_two_sided"], m["final_n"], m["listed_wins"], m["filler_wins"], m["p_two_sided"])


def c4_unpublished_is_loss():
    """Listed slot never published by d7: filler wins that pair."""
    a, e = base()
    e = [x for x in e if not (x["pair_id"] == "p0" and x["slot"] == "slot1")]
    r, m = run(a, e), run(a, e, drop_unpublished)
    good = (r["listed_wins"], r["filler_wins"], r["final_n"]) == (7, 2, 9)
    caught = m["final_n"] == 8
    return good and caught, "real %d-%d n=%d | drop %d-%d n=%d" % (
        r["listed_wins"], r["filler_wins"], r["final_n"], m["listed_wins"], m["filler_wins"], m["final_n"])


def c5_ties_dropped_and_reported():
    a, e = base()
    e[2]["d7_views"] = 200  # p1 tie: listed slot set equal to filler (200)
    r, m = run(a, e), run(a, e, ties_as_losses)
    good = r["ties_dropped"] == 1 and r["final_n"] == 8
    caught = m["final_n"] != 8
    return good and caught, "real ties=%d n=%d | as-loss n=%d" % (r["ties_dropped"], r["final_n"], m["final_n"])


def c6_thresholds():
    """Pre-registered table: 10/10 .002, 9/10 .021, 8/10 .11, 7/10 .34; 8/10 is 'not shown'."""
    got = [round(A.sign_p(k, 10), 3) for k in (10, 9, 8, 7)]
    a, e = base()  # turn into 10 pairs, 8-2
    a.append(asg("p9")); e += [ep("p9", "slot1", "L-p9", 1), ep("p9", "slot2", "F-p9", 2)]
    r = run(a, e)
    ok = got == [0.002, 0.021, 0.109, 0.344] and r["verdict"] == "not shown" and r["final_n"] == 10
    return ok, "p %s; 8/10 -> %s" % (got, r["verdict"])


CASES = [c0_control, c1_tag_lost, c2_filler_swapped, c3_late_assignment,
         c4_unpublished_is_loss, c5_ties_dropped_and_reported, c6_thresholds]

if __name__ == "__main__":
    bad = 0
    for c in CASES:
        ok, msg = c()
        bad += not ok
        print("%s %-30s %s" % ("PASS" if ok else "FAIL", c.__name__, msg))
    print("%d/%d PASS" % (len(CASES) - bad, len(CASES)))
    sys.exit(1 if bad else 0)

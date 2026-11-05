"""Score a coder's labels against truth.jsonl: TP/FP/FN/TN per code, rates with Wilson 95%
intervals, and which classes the errors fall in.

  python3 score.py coder.jsonl [--truth truth.jsonl]
coder.jsonl: one {"id": ..., "S": 0|1, "P": 0|1} per line. A missing or unparseable label
counts as its own column (missing), never as 0.
Exit 0 = no errors, 1 = errors, 3 = nothing checked (no ids matched).
"""
import json, sys, math, collections

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)

def main(argv):
    tpath = argv[argv.index("--truth") + 1] if "--truth" in argv else "truth.jsonl"
    truth = {r["id"]: r for r in map(json.loads, open(tpath))}
    got = {}
    for line in open(argv[1]):
        if line.strip():
            r = json.loads(line); got[r["id"]] = r
    matched = [i for i in truth if i in got]
    if not matched:
        print("nothing checked: no coder ids match truth"); return 3
    errors = 0
    for code in ("S", "P"):
        m = collections.Counter(); bycls = collections.Counter()
        for i in truth:
            t, g = truth[i][code], got.get(i, {}).get(code)
            if g not in (0, 1):
                m["missing"] += 1; continue
            key = {(1, 1): "TP", (0, 1): "FP", (1, 0): "FN", (0, 0): "TN"}[(t, g)]
            m[key] += 1
            if key in ("FP", "FN"):
                bycls[(key, truth[i]["class"])] += 1
        errors += m["FP"] + m["FN"]
        neg, pos = m["FP"] + m["TN"], m["TP"] + m["FN"]
        fl, fh = wilson(m["FP"], neg); nl, nh = wilson(m["FN"], pos)
        print(f"{code}: TP {m['TP']} FP {m['FP']} FN {m['FN']} TN {m['TN']} missing {m['missing']}"
              f" | FP rate {m['FP']}/{neg} [{fl:.2f},{fh:.2f}] FN rate {m['FN']}/{pos} [{nl:.2f},{nh:.2f}]")
        for (k, cls), n in sorted(bycls.items()):
            print(f"   {k} {n} in {cls}")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

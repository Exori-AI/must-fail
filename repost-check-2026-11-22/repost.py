#!/usr/bin/env python3
"""repost.py -- did I post the same idea twice within 7 days? Re-run my repeat check on my public posts.

  python3 repost.py replay posts.jsonl --since 2026-11-19 [--mutant NAME]
  python3 repost.py selftest posts.jsonl          # base must PASS every expectation; every mutant must FAIL one

posts.jsonl: one row per post, {"at": ISO-Z, "name": "x:<post id>" | "tc:<id8>", "text": ...}.
x rows are the full text of my X posts (open x.com/i/status/<id> to check them); tc rows are thecolony.cc
post titles only. Standard library only. Nothing is written.

Score of a post vs each post in the 7 days before it:
  nums  = shared number tokens ($4.77, 1,200 ...), years and 0-3 dropped
  jac   = Jaccard of content words (>= 4 letters, stopwords dropped)
  first = first lines equal after normalising
  HIT if first, or (nums >= 2 and jac >= 0.15), or jac >= 0.35.
The thresholds are picks, not fits. Of the four known repeats below, the last two HIT only through the
nums rule: reworded, same numbers.

Mutants (each is a real or proposed version of the check; each must fail selftest):
  first-line   HIT only on equal first lines (my first proposal, 2026-11-20)
  no-nums      drop the shared-number rule
  name-filter  the --since filter compares name text instead of time (the bug a colony agent found 11-21)
"""
import json, re, sys, datetime as dt

STOP = set("""that this with from have were they them their there what when your about would which
just into than then been being over only also more most some such very will each other because
before after again could should these those while where does doesn't didn't don't it's i'm we're
ours ourselves itself""".split())

# Known repeats: (later post, earlier post). Both are on x.com; read them.
MUST_HIT = [
    ("x:2123567786702082072", "x:2123418922888073279"),  # ~700 agents / Hugging Face, different first line
    ("x:2123631646872088748", "x:2123454242996338879"),  # $4.77 for 45 checks, same first line
    ("x:2122850859755135348", "x:2122438618811679102"),  # 35 posts / 1,188 views again; jac 0.28, numbers only
    ("tc:cd3a4651", "x:2123180504044441857"),            # 15 of 18 videos killed, X then tc title; jac 0.29
]


def norm_line(s):
    return re.sub(r"[^a-z0-9$]+", " ", s.lower()).strip()


def nums(t):
    out = set()
    for m in re.findall(r"\$?\d[\d,]*(?:\.\d+)?%?", t):
        v = m.replace(",", "")
        if re.fullmatch(r"20\d\d", v) or v in ("0", "1", "2", "3"):
            continue
        out.add(v)
    return out


def words(t):
    return {w for w in re.findall(r"[a-z][a-z'\-]+", t.lower()) if len(w) >= 4 and w not in STOP}


def score(a, b, mutant=None):
    wa, wb = words(a), words(b)
    jac = len(wa & wb) / max(1, len(wa | wb))
    sn = nums(a) & nums(b)
    fa = norm_line(a.strip().splitlines()[0]) if a.strip() else ""
    fb = norm_line(b.strip().splitlines()[0]) if b.strip() else ""
    first = bool(fa) and fa == fb
    if mutant == "first-line":
        return first, jac, sorted(sn), first
    if mutant == "no-nums":
        return first or jac >= 0.35, jac, sorted(sn), first
    return first or (len(sn) >= 2 and jac >= 0.15) or jac >= 0.35, jac, sorted(sn), first


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        rows.append((dt.datetime.strptime(d["at"], "%Y-%m-%dT%H:%M:%SZ"), d["name"], d["text"]))
    rows.sort()
    return rows


def in_window(t, name, since, mutant):
    if mutant == "name-filter":
        return name[:8] >= since.strftime("%Y%m%d")  # "x:2123..." and "tc:..." both sort after "2026..."
    return t >= since


def replay(rows, since, mutant=None):
    counted, hits = [], []
    for t, name, text in rows:
        if not in_window(t, name, since, mutant):
            continue
        counted.append(name)
        for pt, pn, prior in rows:
            if pn != name and t - dt.timedelta(days=7) <= pt < t:
                hit, jac, sn, first = score(text, prior, mutant)
                if hit:
                    hits.append((name, pn, jac, sn, first))
    canary = {}
    for p in ("x", "tc"):
        old = [nm for t, nm, _ in rows if nm.startswith(p + ":") and t < since]
        canary[p] = (old[-1], old[-1] not in counted) if old else (None, None)
    return counted, hits, canary


def checks(rows, mutant=None):
    since = dt.datetime(2026, 11, 18)
    counted, hits, canary = replay(rows, since, mutant)
    pairs = {(a, b) for a, b, *_ in hits}
    out = [(f"HIT {a} ~ {b}", (a, b) in pairs) for a, b in MUST_HIT]
    for p, (nm, ok) in canary.items():
        out.append((f"canary {p}: {nm} (newest row before 2026-11-18) not counted", bool(ok)))
    return out


def main(argv):
    if len(argv) < 2 or argv[0] not in ("replay", "selftest"):
        print(__doc__); return 2
    rows = load(argv[1])
    mutant = argv[argv.index("--mutant") + 1] if "--mutant" in argv else None
    if argv[0] == "replay":
        since = dt.datetime.strptime(argv[argv.index("--since") + 1], "%Y-%m-%d") if "--since" in argv else dt.datetime.min
        counted, hits, canary = replay(rows, since, mutant)
        for a, b, jac, sn, first in hits:
            print(f"HIT {a} ~ {b} jac={jac:.2f} nums={sn} first_line={first}")
        n_hit = len({a for a, *_ in hits})
        print(f"replay: {len(counted)} posts counted, {n_hit} with a HIT, {len(hits)} pairs")
        for p, (nm, ok) in canary.items():
            print(f"canary {p}: {nm} " + ("excluded ok" if ok else "NONE" if ok is None else "COUNTED: FILTER BROKEN"))
        return 5 if any(ok is False for _, ok in canary.values()) else 0
    bad = 0
    for m in (None, "first-line", "no-nums", "name-filter"):
        res = checks(rows, m)
        passed = all(ok for _, ok in res)
        want = m is None
        bad += passed != want
        print(f"{m or 'base':12} {'PASS' if passed else 'FAIL'} (must {'PASS' if want else 'FAIL'})"
              + ("" if passed == want else "  <-- WRONG"))
        for label, ok in res:
            if not ok:
                print(f"    failed: {label}")
    print("selftest " + ("ok" if not bad else f"BROKEN ({bad})"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

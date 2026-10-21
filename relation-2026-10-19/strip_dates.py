#!/usr/bin/env python3
"""v5 part (a) on scientist's relation set: strip calendar dates only, then run v4 unchanged.
Clock times (14:00, 09:00) stay: in b07 the time is the claimed value, not an as-of stamp.
Prints the v4 link table on raw text vs date-stripped text, per true relation kind (key is open since Touchstone 299).
Re-run: python3 strip_dates.py   (from this folder)."""
import hashlib, importlib.util, re, collections
L = "v4_match.py"
s = importlib.util.spec_from_file_location("v4", L); v4 = importlib.util.module_from_spec(s); s.loader.exec_module(v4)
for f, want in (("claims.txt", "dc5ab9c0"), ("lines.txt", "3fd0ae6c")):
    assert hashlib.sha256(open(f, "rb").read()).hexdigest()[:8] == want, f
MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATES = [
    r"\b20\d\d-\d\d-\d\d\b",                       # 2026-10-17
    r"\b\d{1,2}/\d{1,2}/20\d\d\b",                 # 10/16/2026
    rf"\b\d{{1,2}}\s+{MON}(?:\s+20\d\d)?\b",       # 14 Oct 2026, 9 Oct
    rf"\b{MON}\s+\d{{1,2}}(?:,?\s+20\d\d)?\b",     # Oct 16, Oct 18
]
DRX = re.compile("|".join(DATES), re.I)
def strip(t): return DRX.sub(" ", t)
def rows(f): return [ln.split("\t", 1) for ln in open(f).read().splitlines() if ln and not ln.startswith("#")]
def hit4(claim, ln):
    cn, cs = v4.fields(claim)
    return any(len(cn & n) >= 1 and len(cs & s) >= 2 for n, s in map(v4.fields, v4.chunks(ln)))
key = {r[0]: r[1:] for r in (l.split("\t") for l in open("KEY.tsv").read().splitlines() if l and not l.startswith("#"))}
claims, lines = rows("claims.txt"), rows("lines.txt")
tab = collections.defaultdict(lambda: [0, 0, 0])  # kind -> [n, raw links to own base, stripped links to own base]
stray = {"raw": 0, "stripped": 0}
changed = []
for lid, lt in lines:
    base, kind = key[lid][0], key[lid][1]
    tab[kind][0] += 1
    for cid, ct in claims:
        r, st = hit4(ct, lt), hit4(strip(ct), strip(lt))
        if cid == base:
            tab[kind][1] += r; tab[kind][2] += st
            if r != st: changed.append(f"{cid} {lid} {kind}: {int(r)} -> {int(st)}")
        else:
            stray["raw"] += r; stray["stripped"] += st
print("kind\tn\tv4_raw\tv4_dates_stripped")
for k in ("same", "corrects", "conflicts", "supersedes", "unrelated"):
    n, a, b = tab[k]; print(f"{k}\t{n}\t{a}\t{b}")
print(f"links to a wrong base: raw {stray['raw']}, stripped {stray['stripped']}")
print("changed:", *changed, sep="\n  ")

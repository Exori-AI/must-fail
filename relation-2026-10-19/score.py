#!/usr/bin/env python3
"""Score planted_check v4 (unmodified, imported) on scientist's relation set (key sha b28b51cf, Touchstone 285).
Directed: each base claim b01-b10 -> every line L01..Lnn. Prints claim, line, v4 link (0/1).
Key is NOT read here. Join with KEY-sealed.tsv only after this output is hashed and logged."""
import hashlib, importlib.util, sys
L = "v4_match.py"
s = importlib.util.spec_from_file_location("v4", L); v4 = importlib.util.module_from_spec(s); s.loader.exec_module(v4)
print("# v4", hashlib.sha256(open(L, "rb").read()).hexdigest()[:8], file=sys.stderr)
for f, want in (("claims.txt", "dc5ab9c0"), ("lines.txt", "3fd0ae6c")):
    got = hashlib.sha256(open(f, "rb").read()).hexdigest()[:8]
    assert got == want, (f, got, want)
def rows(f):
    return [ln.split("\t", 1) for ln in open(f).read().splitlines() if ln and not ln.startswith("#")]
def hit4(claim, ln):
    cn, cs = v4.fields(claim)
    return any(len(cn & n) >= 1 and len(cs & s) >= 2 for n, s in map(v4.fields, v4.chunks(ln)))
print("claim\tline\tv4")
for cid, ct in rows("claims.txt"):
    for lid, lt in rows("lines.txt"):
        print(f"{cid}\t{lid}\t{int(hit4(ct, lt))}")

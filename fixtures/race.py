#!/usr/bin/env python3
"""race.py: listing-then-open swaps for claim.py --root (nuntius, fork.zone c702, 2026-11-07).

claim.py lists each name, then opens it. A swap in between used to pass: the rename case
(move an outside file over the listed name) was accepted, because the opened file has one
link and the realpath was checked before the swap. Deterministic: os.open is hooked to do
the swap right before claim.py opens the name. In-process only; --cmd can't express this.

  python3 fixtures/race.py      exit 0 if every case got its expected verdict
"""
import hashlib, os, sys, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("claim", os.path.join(HERE, "..", "examples", "claim.py"))
claim = importlib.util.module_from_spec(spec); spec.loader.exec_module(claim)

def run(swap):
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "root"); os.mkdir(root)
        inside, outside = os.path.join(root, "report.txt"), os.path.join(d, "secret.txt")
        open(inside, "wb").write(b"inside\n"); open(outside, "wb").write(b"outside\n")
        want = hashlib.sha256(b"inside\n" if swap is None else b"outside\n").hexdigest()
        raw = f"verified.\nread: report.txt sha256:{want}\n"
        real_open = os.open
        def hooked(path, *a, **k):
            if path.endswith("report.txt"):
                if swap == "rename":
                    os.rename(outside, inside)
                elif swap == "hardlink":
                    os.unlink(inside); os.link(outside, inside)
            return real_open(path, *a, **k)
        os.open = hooked
        try:
            return claim.root_mismatch(raw, root)
        finally:
            os.open = real_open

CASES = [
    ("no-swap", None, "accept", "control: the listed file is the opened file"),
    ("rename-swap", "rename", "refuse", "outside file renamed over the name after listing (was accepted before 2026-11-07)"),
    ("hardlink-swap", "hardlink", "refuse", "name replaced by a hard link to an outside file after listing"),
]

bad = 0
for cid, swap, expect, why in CASES:
    msg = run(swap)
    got = "accept" if msg is None else "refuse"
    bad += got != expect
    print(f"{'ok  ' if got == expect else 'FAIL'} {cid:14} expect={expect:6} got={got:6} {why}" + (f" | {msg}" if msg else ""))
print(f"{len(CASES) - bad}/{len(CASES)} race cases got the expected verdict")
sys.exit(1 if bad else 0)

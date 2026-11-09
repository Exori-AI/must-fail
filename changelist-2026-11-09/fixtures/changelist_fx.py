#!/usr/bin/env python3
"""Fixtures for changelist.check. Exits 1 if any verdict is wrong.
Synthetic texts; the bug shape (label from a whitespace-collapsed find across a line wrap) is the one
deep-seeker found in a real filing on 2026-11-09."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from changelist import check

OLD = "A receipt names the read.\nIt also names   the\nwriter, and the time it was read.\nEnd."
F1, R1 = "It also names   the\nwriter, and", "It names the writer and"
F2, R2 = "the time it was read.", "read_at."
NEW = OLD.replace(F1, R1).replace(F2, R2)
d1 = len(R1) - len(F1); d2 = len(R2) - len(F2)
buggy1 = len(R1) - len(" ".join(F1.split()))          # the collapsed-find label: wrong by the extra whitespace

def it(n, label, f=None, r=None):
    x = {"name": n, "label": label}
    if f is not None: x.update(find=f, rep=r)
    return x

CASES = [
    ("correct list, per item", [it("C1", d1, F1, R1), it("C2", d2, F2, R2)], "closes"),
    ("correct list, labels only", [it("C1", d1), it("C2", d2)], "closes"),
    # must-fail
    ("collapsed-find label (the 11-09 shape)", [it("C1", buggy1, F1, R1), it("C2", d2, F2, R2)], "sum_fails"),
    ("offsetting errors, per item", [it("C1", d1 + 3, F1, R1), it("C2", d2 - 3, F2, R2)], "item_fails"),
    ("ambiguous find (two places it could apply)", [it("C0", 0, "names", "names"), it("C1", d1, F1, R1), it("C2", d2, F2, R2)], "unappliable"),
    ("find no longer present", [it("C1", d1, F1, R1), it("C2", d2, "not in text", R2)], "unappliable"),
    ("same-length swap: labels right, text wrong", [it("C1", d1, F1, R1), it("C2", d2, F2, "read_at!")], "unappliable"),
]
# the honest limit: labels-only cannot see offsetting errors; this one is EXPECTED to (wrongly) close
LIMIT = ("offsetting errors, labels only", [it("C1", d1 + 3), it("C2", d2 - 3)], "closes")

bad = 0
for name, items, want in CASES + [LIMIT]:
    got, why = check(OLD, NEW, items)
    ok = got == want; bad += not ok
    print(f'{"ok  " if ok else "FAIL"} {name}: {got} (want {want}) - {why}')
print(f"{len(CASES) + 1 - bad}/{len(CASES) + 1} as expected (the last is the known blind spot of a sum-only check)")
sys.exit(1 if bad else 0)

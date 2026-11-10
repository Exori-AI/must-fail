#!/usr/bin/env python3
"""Fixtures for keepdiff.check, plus 3 mutants that must each get caught. Exits 1 if any verdict is wrong
or any mutant survives. Builds every case in a temp dir; needs python3 and git, nothing else."""
import json, os, sys, tempfile, types

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keepdiff.py")
BUG = "def add(a, b):\n    return a - b\n"
OK = "def add(a, b):\n    return a + b\n"
TEST = "import calc\nassert calc.add(2, 2) == 4\n"
FIX = "--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
NOOP = "--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n-def add(a, b):\n+def add(a, b):  # tidy\n     return a - b\n"
CHEAT = "--- a/test_calc.py\n+++ b/test_calc.py\n@@ -1,2 +1,2 @@\n import calc\n-assert calc.add(2, 2) == 4\n+assert calc.add(2, 2) == 0\n"
TIDY = "--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n-def add(a, b):\n+def add(a, b):  # tidy\n     return a + b\n"
STALE = "--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(x, y):\n-    return x * y\n+    return x + y\n"

# (name, calc.py on base, patch text or None, want PASS?)
CASES = [
    ("kept patch fixes the bug", BUG, FIX, True),
    # must-fail
    ("fix claimed, no patch saved", BUG, None, False),
    ("fix claimed, empty patch file", BUG, "", False),
    ("patch edits the test, not the code", BUG, CHEAT, False),
    ("base already passes (bug never shown)", OK, FIX, False),
    ("base already passes, patch applies", OK, TIDY, False),
    ("patch applies, test still fails", BUG, NOOP, False),
    ("patch from another version (won't apply)", BUG, STALE, False),
]

def build(root, i, base_src, patch):
    d = os.path.join(root, "c%d" % i)
    os.makedirs(os.path.join(d, "base"))
    open(os.path.join(d, "base", "calc.py"), "w").write(base_src)
    open(os.path.join(d, "base", "test_calc.py"), "w").write(TEST)
    rec = {"claim": "fixed", "base": "base", "test": [sys.executable, "test_calc.py"], "tests": ["test_calc.py"], "patch": None}
    if patch is not None:
        open(os.path.join(d, "fix.diff"), "w").write(patch)
        rec["patch"] = "fix.diff"
    p = os.path.join(d, "record.json")
    json.dump(rec, open(p, "w"))
    return p

def load(src):
    m = types.ModuleType("kd"); exec(compile(src, "keepdiff", "exec"), m.__dict__); return m

def score(mod, recs):
    return [mod.check(p)[0] == want for p, (_, _, _, want) in zip(recs, CASES)]

src = open(SRC).read()
MUTANTS = [
    ("trusts the claim when no patch was saved",
     'return False, "fix claimed, no patch saved: unfalsifiable"', 'return True, "trusted"'),
    ("never runs the test on base",
     'if run_test(b, rec["test"]):', 'if False:'),
    ("lets the patch edit the test",
     'hit = touched & set(rec.get("tests", []))', 'hit = set()'),
]
with tempfile.TemporaryDirectory() as root:
    recs = [build(root, i, c[1], c[2]) for i, c in enumerate(CASES)]
    real = load(src)
    bad = 0
    for p, (name, _, _, want) in zip(recs, CASES):
        ok, why = real.check(p)
        good = ok == want
        bad += not good
        print(f'{"ok  " if good else "FAIL"} {name}: {"PASS" if ok else "FAIL"} {why}')
    print(f"{len(CASES) - bad}/{len(CASES)} correct")
    survived = 0
    for name, old, new in MUTANTS:
        assert old in src, name
        caught = not all(score(load(src.replace(old, new)), recs))
        survived += not caught
        print(f'{"caught  " if caught else "SURVIVED"} mutant: {name}')
sys.exit(1 if bad or survived else 0)

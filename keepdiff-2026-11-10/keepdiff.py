#!/usr/bin/env python3
"""keepdiff: a claimed fix is checkable only if the patch was kept.

Usage: keepdiff.py <record.json>
record = {"claim": "fixed", "base": "<dir>", "patch": "<file or null>", "test": ["argv", ...], "tests": ["<path in base>", ...]}
Paths are relative to the record's directory. Exit 0 = PASS, 1 = FAIL, with one reason line.

PASS needs all of: the patch was saved and is non-empty; it applies to a copy of base; it touches no file listed
in "tests"; the test FAILS on base (the bug is shown); the test PASSES with the patch (the fix is shown).
Undo the patch and you are back on base, so the same run is the revert check (evals_ag, X 2119765446417416432).
"""
import json, os, re, shutil, subprocess, sys, tempfile

def run_test(d, argv):
    # No bytecode cache: "a - b" -> "a + b" keeps size and can keep mtime, so a .pyc from the base run would
    # be reused and the fix would look like it failed (it did, in the first fixture run).
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(argv, cwd=d, capture_output=True, timeout=60, env=env).returncode == 0

def check(rec_path):
    here = os.path.dirname(os.path.abspath(rec_path))
    rec = json.load(open(rec_path))
    if rec.get("claim") != "fixed":
        return False, "no fix claimed: nothing to check"
    if not rec.get("patch"):
        return False, "fix claimed, no patch saved: unfalsifiable"
    patch = os.path.join(here, rec["patch"])
    if not os.path.isfile(patch) or os.path.getsize(patch) == 0:
        return False, "fix claimed, patch file missing or empty: unfalsifiable"
    text = open(patch, encoding="utf-8", errors="replace").read()
    touched = set(re.findall(r"^\+\+\+ b/(\S+)", text, re.M)) | set(re.findall(r"^--- a/(\S+)", text, re.M))
    if not touched:
        return False, "patch has no file headers: not a unified diff"
    hit = touched & set(rec.get("tests", []))
    if hit:
        return False, "patch edits the test: %s" % ", ".join(sorted(hit))
    with tempfile.TemporaryDirectory() as t:
        b = os.path.join(t, "b")
        shutil.copytree(os.path.join(here, rec["base"]), b)
        if run_test(b, rec["test"]):
            return False, "test already passes on base: the bug was never shown"
        r = subprocess.run(["git", "apply", "--unsafe-paths", "--directory=.", os.path.abspath(patch)],
                           cwd=b, capture_output=True)
        if r.returncode != 0:
            return False, "patch does not apply to base"
        if not run_test(b, rec["test"]):
            return False, "test still fails with the patch: no fix shown"
    return True, "bug shown on base, fixed by the kept patch"

if __name__ == "__main__":
    ok, why = check(sys.argv[1])
    print(("PASS " if ok else "FAIL ") + why)
    sys.exit(0 if ok else 1)

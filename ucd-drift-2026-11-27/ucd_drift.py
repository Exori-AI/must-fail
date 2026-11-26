#!/usr/bin/env python3
"""NFKC result depends on the Unicode data version: a must-fail fixture (exori 2026-11-26, for dantic 50c0555e).

Unicode's normalization stability policy freezes the mapping of characters that are already assigned.
Drift comes from NEW assignments. U+1E030..U+1E08F (Cyrillic Extended-D) is unassigned in UCD 14.0.0.
In 15.0.0, 62 of those characters have <super> compatibility decompositions; e.g. U+1E030 MODIFIER LETTER
CYRILLIC SMALL A -> <super> 0430. So NFKC("\\U0001E030") is the input unchanged on UCD 14 and "\\u0430" on 15+.
A filter that NFKC-folds and then checks scripts gives different verdicts on the same bytes on two machines.

Sources (fetched 2026-11-26):
  https://www.unicode.org/Public/14.0.0/ucd/UnicodeData.txt  sha256 36018e68657fdcb3485f636630ffe8c8532e01c977703d2803f5b89d6c5feafb (no 1E030 line)
  https://www.unicode.org/Public/15.0.0/ucd/UnicodeData.txt  sha256 806e9aed65037197f1ec85e12be6e8cd870fc5608b4de0fffd990f689f376a73
    1E030;MODIFIER LETTER CYRILLIC SMALL A;Lm;0;L;<super> 0430;;;;N;;;;;

Rule this enforces: a canonicalized row must carry unicodedata.unidata_version, and two rows with
different versions are refused as a comparison pair (exit 1), not compared.
"""
import json, os, sys, unicodedata

# dantic 2dd0f9e7: assert the live database, don't just print it. CI sets MUSTFAIL_EXPECT_UCD; a mismatch exits 1.
# (CPython 3.11 ships 14.0.0 and 3.12 ships 15.0.0, per docs.python.org/3/whatsnew/3.11.html and 3.12.html.)
EXPECT_UCD = os.environ.get("MUSTFAIL_EXPECT_UCD")

PROBE = "\U0001E030"
EXPECT = {"14.0.0": PROBE}            # unassigned: NFKC leaves it unchanged
EXPECT_15_PLUS = "а"             # 15.0.0 and later: <super> 0430

def row(text):
    return {"ucd": unicodedata.unidata_version, "py": sys.version.split()[0],
            "nfkc": unicodedata.normalize("NFKC", text)}

def comparable(a, b):
    return a["ucd"] == b["ucd"]

def selftest():
    r = row(PROBE)
    v = tuple(int(x) for x in r["ucd"].split("."))
    want = EXPECT_15_PLUS if v >= (15, 0, 0) else PROBE
    assert r["nfkc"] == want, (r, want)
    # must-fail: a pair across UCD versions is refused even when the outputs happen to match
    a = {"ucd": "14.0.0", "py": "3.11", "nfkc": PROBE}
    b = {"ucd": "15.0.0", "py": "3.12", "nfkc": EXPECT_15_PLUS}
    assert not comparable(a, b)
    assert not comparable(a, dict(b, nfkc=PROBE))
    return r

if __name__ == "__main__":
    if EXPECT_UCD and unicodedata.unidata_version != EXPECT_UCD:
        print(json.dumps({"ok": False, "want_ucd": EXPECT_UCD, "live_ucd": unicodedata.unidata_version})); sys.exit(1)
    r = selftest()
    print(json.dumps({"ok": True, "here": {"ucd": r["ucd"], "py": r["py"], "nfkc_U+1E030": [hex(ord(c)) for c in r["nfkc"]]}}))

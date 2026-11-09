#!/usr/bin/env python3
"""Fixtures for tombstone.classify. Exits 1 if any verdict is wrong.
Bodies 1-3 are the bytes thecolony.cc served on 2026-11-09 07:40:59Z (control body truncated: only status matters)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tombstone import classify

GONE = b'{"detail":{"message":"This comment has been deleted.","code":"COMMENT_GONE"}}'
NF = b'{"error":"not_found","status":404,"path":"/api/v1/comments/f65a62f2-3513-44de-89c8-9f3d06e8807c","detail":{"message":"Comment not found.","code":"NOT_FOUND"}}'
CASES = [
    ("live comment", 200, b'{"id":"cd906987-dea1-437d-b9c5-19e1e32ba00c"}', "present"),
    ("deleted comment", 410, GONE, "deleted"),
    ("random uuid", 404, NF, "never"),
    # must-fail: shapes a lazy checker would fold into a neighbour
    ("410 without the gone code", 410, b'{"detail":{"code":"NOT_FOUND"}}', "unknown"),
    ("404 carrying the gone code", 404, GONE, "unknown"),
    ("404 with an empty body", 404, b"", "unknown"),
    ("403 (private, not absent)", 403, b'{"detail":{"code":"FORBIDDEN"}}', "unknown"),
    ("500 during an outage", 500, b"<html>", "unknown"),
    ("429 rate limit", 429, b'{"detail":{"code":"RATE_LIMITED"}}', "unknown"),
]

bad = 0
for name, status, body, want in CASES:
    got = classify(status, body)
    ok = got == want
    bad += not ok
    print(f'{"ok  " if ok else "FAIL"} {name}: {got} (want {want})')
print(f"{len(CASES) - bad}/{len(CASES)} correct")
sys.exit(1 if bad else 0)

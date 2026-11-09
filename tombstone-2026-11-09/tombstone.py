#!/usr/bin/env python3
"""Classify an object id as present / deleted / never / unknown from one GET, no auth.

Question from huilai-rushi (thecolony.cc, shenwuan-way): can an outsider tell "existed, now gone"
from "never existed"? On thecolony.cc's comment route, on 2026-11-09, yes:
  live    -> 200
  deleted -> 410 {"detail":{"code":"COMMENT_GONE",...}}
  bogus   -> 404 {"detail":{"code":"NOT_FOUND",...}}

  python3 tombstone.py <id> [<id> ...] [--base https://thecolony.cc/api/v1/comments] [--json]

The witness is still the platform. 'deleted' means the platform says so; it says nothing about
what the object said or who removed it. Anything that is not exactly one of the three shapes
above is 'unknown', never folded into a neighbour.
"""
import hashlib, json, sys, urllib.error, urllib.request

def classify(status, body):
    try:
        code = (json.loads(body or b"{}").get("detail") or {}).get("code")
    except (ValueError, AttributeError):
        code = None
    if status == 200:
        return "present"
    if status == 410 and code == "COMMENT_GONE":
        return "deleted"
    if status == 404 and code == "NOT_FOUND":
        return "never"
    return "unknown"

def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def main(argv):
    base = "https://thecolony.cc/api/v1/comments"
    if "--base" in argv:
        i = argv.index("--base"); base = argv[i + 1]; del argv[i:i + 2]
    as_json = "--json" in argv
    ids = [a for a in argv if a != "--json"]
    if not ids:
        print(__doc__); return 2
    for cid in ids:
        status, body = fetch(f"{base}/{cid}")
        row = {"id": cid, "status": status, "state": classify(status, body),
               "body_sha256": hashlib.sha256(body).hexdigest()}
        print(json.dumps(row) if as_json else f'{row["state"]:8} {status} {cid} {row["body_sha256"][:16]}')
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

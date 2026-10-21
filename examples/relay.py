#!/usr/bin/env python3
"""relay.py: check that a relayed action is the one the approver approved.

The failure this answers: an approval passes through a relay (a queue, a sender agent,
a proxy) that logs what it received and what it forwarded. A verifier that only checks
the relay's two entries against each other and against the action proves the relay is
self-consistent, not honest. A relay that swaps the action and rewrites both entries to
match passes that check.

Fix: compare against a record the relay never had write access to, the approver's own
hash of what it approved (the anchor, kept on the approver's side). Both relay entries
agreeing while the anchor disagrees is a refusal, not a pass.
(Case from Crescitaly, r/AI_Agents, 2026-10-20.)

  relay.py verify --anchors FILE   stdin JSON {approval_id, action, received_sha, forwarded_sha}
                                   rc 0 + "ok" if action, both relay entries and the anchor agree;
                                   rc 1, stdout empty, otherwise
  relay.py naive                   same input, ignores the anchor (for contrast: it accepts the swap)

FILE is JSONL, one {approval_id, sha256} per line, written by the approver.
"""
import argparse, hashlib, json, sys

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def relay_consistent(r):
    h = sha(r["action"])
    return r["received_sha"] == h and r["forwarded_sha"] == h

def anchors(path):
    out = {}
    for ln in open(path, encoding="utf-8"):
        if ln.strip():
            row = json.loads(ln)
            if row["approval_id"] in out and out[row["approval_id"]] != row["sha256"]:
                out[row["approval_id"]] = None  # two different hashes for one approval: trust neither
            else:
                out[row["approval_id"]] = row["sha256"]
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--anchors", required=True)
    sub.add_parser("naive")
    a = ap.parse_args()
    try:
        r = json.loads(sys.stdin.read())
        if not relay_consistent(r):
            print("refused: relay entries disagree with the action", file=sys.stderr); return 1
        if a.cmd == "verify":
            want = anchors(a.anchors).get(r["approval_id"])
            if want is None or want != sha(r["action"]):
                print("refused: approver anchor missing or disagrees", file=sys.stderr); return 1
    except (ValueError, KeyError, TypeError) as e:
        print(f"refused: bad input ({type(e).__name__})", file=sys.stderr); return 1
    print("ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())

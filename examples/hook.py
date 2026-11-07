#!/usr/bin/env python3
"""hook.py: check that a hook was approved by someone other than the party that installed it.

The failure this answers: an installer adds a hook to a harness settings file and also writes
the hook's trusted_hash next to it. A check that only compares the hook to trusted_hash reads
a claim the installer made about itself, so it passes. (postmanlabs/postman-app-support #14370,
2026-10-24: Postman Desktop's Codex installer wrote its own hook's trusted_hash; reverted per
staff 11-05. Rule from gavinagent and mark, thecolony b12d1be6, 2026-11-07: a record the
approved party can write records nothing; a grant names the artifact, not the publisher.)

Fix: compare against the user's own grant log, kept where the installer can't write. A grant
names one hook by sha256. "Everything from this publisher" is not a grant for a hook.

  hook.py verify --grants FILE   stdin JSON {hook_id, command, trusted_hash, written_by}
                                 rc 0 + "ok" if the command hashes to trusted_hash AND FILE
                                 holds exactly one sha256 for hook_id, equal to the command's,
                                 granted by someone other than written_by; rc 1 otherwise
  hook.py naive                  same input, checks only command vs trusted_hash (accepts the
                                 Postman shape, for contrast)

FILE is JSONL, one {hook_id, sha256, by} per line (or {publisher, scope, by} for a blanket
grant, which never counts). Limit: the checker can't see who can write FILE. Keeping it out
of the installer's reach is the deployment's job, and `by` is only as good as that.
"""
import argparse, hashlib, json, sys

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def grants(path, hook_id):
    rows = []
    for ln in open(path, encoding="utf-8"):
        if ln.strip():
            g = json.loads(ln)
            if g.get("hook_id") == hook_id and g.get("sha256"):
                rows.append(g)
    return rows

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--grants", required=True)
    sub.add_parser("naive")
    a = ap.parse_args()
    try:
        h = json.loads(sys.stdin.read())
        if sha(h["command"]) != h["trusted_hash"]:
            print("refused: command doesn't hash to trusted_hash", file=sys.stderr); return 1
        if a.cmd == "verify":
            rows = grants(a.grants, h["hook_id"])
            if len({g["sha256"] for g in rows}) != 1:
                print("refused: no grant for this hook, or two different hashes", file=sys.stderr); return 1
            if rows[0]["sha256"] != sha(h["command"]):
                print("refused: the hook changed since it was granted", file=sys.stderr); return 1
            if any(g.get("by") == h["written_by"] for g in rows):
                print("refused: the installer granted its own hook", file=sys.stderr); return 1
    except (ValueError, KeyError, TypeError) as e:
        print(f"refused: bad input ({type(e).__name__})", file=sys.stderr); return 1
    print("ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())

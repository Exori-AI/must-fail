#!/usr/bin/env python3
"""Does a filing's change list close against the texts it claims to connect?

  python3 changelist.py <old.txt> <new.txt> <list.json>

list.json: {"items": [{"name": "C1", "label": -162, "find": "...", "rep": "..."}, ...]}
"find"/"rep" are optional. Without them only the SUM is checkable; with them every item is
re-applied in order (exact match, whitespace runs match any run, like build_v5.py's pat()) and
each label is compared with the delta actually applied.

Verdicts: closes | sum_fails | item_fails | unappliable. Exit 0 only for closes.

Shape from deep-seeker on thecolony.cc (034045f1 on 9c0afaad, 2026-11-09): labels computed as
len(rep) - len(collapsed find) summed to +39 against a true +14. The text was right; the list was not.
A sum check alone misses offsetting errors (one item +3 too high, another -3), so per-item wins.
"""
import json, re, sys

def pat(find):
    return re.compile(r"\s+".join(re.escape(w) for w in find.split()))

def check(old, new, items):
    total = len(new) - len(old)
    if sum(i["label"] for i in items) != total:
        return "sum_fails", f'labels sum {sum(i["label"] for i in items):+d}, texts differ by {total:+d}'
    if not all("find" in i and "rep" in i for i in items):
        return "closes", "sum only (no find/rep: offsetting item errors are not ruled out)"
    out = old
    for i in items:
        hits = list(pat(i["find"]).finditer(out)) if i["find"] else []
        if len(hits) != 1:
            return "unappliable", f'{i["name"]}: find matched {len(hits)} times'
        m = hits[0]; before = len(out)
        out = out[:m.start()] + i["rep"] + out[m.end():]
        if len(out) - before != i["label"]:
            return "item_fails", f'{i["name"]}: labelled {i["label"]:+d}, applied {len(out) - before:+d}'
    if out != new:
        return "unappliable", "edits applied in order do not reproduce the new text"
    return "closes", f"{len(items)} items, each label = applied delta, sum {total:+d}"

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(2)
    old, new = (open(p, encoding="utf-8").read() for p in sys.argv[1:3])
    v, why = check(old, new, json.load(open(sys.argv[3]))["items"])
    print(v, "-", why); sys.exit(0 if v == "closes" else 1)

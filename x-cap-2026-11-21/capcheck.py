#!/usr/bin/env python3
"""capcheck.py - check an X account's posting cap from public post IDs alone.

An X post ID is a snowflake: its top bits are the creation time in ms since
2010-11-04T01:42:54.657Z. So a list of IDs is enough to count posts per UTC
day and the gap between posts. No API, no login, no trust in our timestamps.

  python3 capcheck.py ids.txt [--cap 10] [--gap-min 60] [--day 2026-11-21]

ids.txt: one post ID or x.com/.../status/<id> URL per line; '#' starts a comment.
Exit 0 if every day (or --day) is within --cap and every gap >= --gap-min, 1 if not.

What it cannot see: posts missing from the list. The list is ours, so a post we
left out (or deleted) is invisible here. Check the list against the public
timeline yourself; any ID you find there that is not in the list is a fail.
"""
import re, sys, argparse
from datetime import datetime, timezone
from collections import defaultdict

EPOCH_MS = 1288834974657

def ts(i):
    return datetime.fromtimestamp(((i >> 22) + EPOCH_MS) / 1000, tz=timezone.utc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids")
    ap.add_argument("--cap", type=int, default=10)
    ap.add_argument("--gap-min", type=float, default=60)
    ap.add_argument("--day")
    a = ap.parse_args()
    ids = []
    for line in open(a.ids):
        line = line.split("#")[0].strip()
        m = re.search(r"(\d{15,20})\s*$", line)
        if m:
            ids.append(int(m.group(1)))
    rows = sorted((ts(i), i) for i in set(ids))
    days = defaultdict(list)
    for t, i in rows:
        days[t.strftime("%Y-%m-%d")].append((t, i))
    bad = 0
    for d in sorted(days):
        if a.day and d != a.day:
            continue
        posts = days[d]
        over = len(posts) > a.cap
        print(f"{d}  posts={len(posts)}  cap={a.cap}  {'OVER' if over else 'ok'}")
        bad += over
    prev = None
    for t, i in rows:
        if a.day and t.strftime("%Y-%m-%d") != a.day:
            prev = (t, i)
            continue
        gap = (t - prev[0]).total_seconds() / 60 if prev else None
        flag = "  SHORT GAP" if gap is not None and gap < a.gap_min else ""
        bad += bool(flag)
        g = f"{gap:6.1f} min" if gap is not None else "     first"
        print(f"  {t:%Y-%m-%dT%H:%M:%SZ}  {i}  gap {g}{flag}")
        prev = (t, i)
    print("FAIL" if bad else "PASS", f"({bad} problem(s))")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()

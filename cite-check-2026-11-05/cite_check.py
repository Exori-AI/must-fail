#!/usr/bin/env python3
"""cite_check.py — check the rule citations on X why-rows against the stored rule versions.

  cite_check.py --log why-log.jsonl [--store rules-store] [--fence-rule until-blank-or-heading|physical]
                [--window N] [--json]

A row cites a rule as a triple (finch, thecolony 547ad1ae 0761b943): the rule file's version, by the sha256
the row's own receipt carries; a section, by its heading text in that version; and the operative line,
quoted verbatim. Each citation gets three answers:

  in_version     the quote is a substring of one line of the stored copy named by the hash
  under_heading  that line sits under the cited heading (from the heading to the next heading of the
                 same or higher level)
  coverage       always "unjudged". Whether the line names this class of act needs a judge; this script
                 isn't one, and won't print a verdict-shaped guess next to the two real checks

It also prints the lines that follow the quote, so a fence or exception sitting near a quoted permission
shows up even if the citation left it out. The stopping rule is printed with every row:
  fence_rule  until-blank-or-heading (default) or physical
  window      N, the most following lines shown
  stop        boundary (blank line or heading), eof, or cap (cut off at N). gobirinman, 547ad1ae be8bbc56:
              cap is printed apart so a reader knows the neighbours were cut, not finished.
A miss is reported under the printed rule; rerun with the other rule to disagree in numbers.

Exit: 0 every citation passed both checks, 1 at least one failed, 3 no row carried a citation.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def neighbours(lines, i, rule, n):
    out = []
    for line in lines[i + 1:i + 1 + n]:
        if rule == "until-blank-or-heading" and (not line.strip() or HEAD.match(line)):
            return out, "boundary"
        out.append(line)
    return out, "cap" if len(lines) > i + 1 + n else "eof"


def section_of(lines, i):
    """Heading text that governs line i: nearest heading above it (any level)."""
    for j in range(i, -1, -1):
        m = HEAD.match(lines[j])
        if m:
            return m.group(2)
    return None


def check(cite, store, rule, n):
    r = {"file": cite.get("file"), "sha256": cite.get("sha256"), "section": cite.get("section"),
         "quote": cite.get("quote"), "fence_rule": rule, "window": n, "coverage": "unjudged"}
    sha, quote = cite.get("sha256") or "", cite.get("quote") or ""
    f = store / sha
    if not sha or sha == "missing" or not f.exists():
        r.update(in_version="no stored copy", under_heading="not checked", ok=False)
        return r
    b = f.read_bytes()
    if hashlib.sha256(b).hexdigest() != sha:
        r.update(in_version="stored copy does not hash to the cited sha", under_heading="not checked", ok=False)
        return r
    lines = b.decode("utf-8", "replace").splitlines()
    hits = [i for i, l in enumerate(lines) if quote and quote in l]
    if not hits:
        r.update(in_version="no", under_heading="not checked", ok=False)
        return r
    r["in_version"] = f"yes, line {hits[0] + 1}" + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else "")
    under = [i for i in hits if section_of(lines, i) == cite.get("section")]
    if under:
        i = under[0]
        r["under_heading"] = "yes"
    else:
        i = hits[0]
        r["under_heading"] = f"no (line {i + 1} is under '{section_of(lines, i)}')"
    r["following"], r["stop"] = neighbours(lines, i, rule, n)
    r["ok"] = bool(under)
    return r


def main(a):
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--store", default="rules-store")
    p.add_argument("--fence-rule", default="until-blank-or-heading", choices=["until-blank-or-heading", "physical"])
    p.add_argument("--window", type=int, default=4)
    p.add_argument("--json", action="store_true")
    o = p.parse_args(a)
    if o.window < 0:
        p.error("--window must be >= 0")
    rows = [json.loads(l) for l in Path(o.log).read_text().splitlines() if l.strip()]
    cited = [r for r in rows if r.get("cite")]
    res = []
    for row in cited:
        c = check(row["cite"], Path(o.store), o.fence_rule, o.window)
        c["row"] = row.get("hash", "")[:16]
        c["ts"] = row.get("ts")
        res.append(c)
    if o.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for c in res:
            print(f"{c['ts']} {c['row']} {'PASS' if c['ok'] else 'FAIL'} {c['file']}@{(c['sha256'] or '')[:12]}"
                  f" #{c['section']}\n  quote: {c['quote']!r}\n  in_version: {c['in_version']}"
                  f" | under_heading: {c['under_heading']} | coverage: {c['coverage']}")
            if "stop" in c:
                print(f"  fence_rule: {c['fence_rule']} window: {c['window']} stop: {c['stop']}")
                for l in c["following"]:
                    print(f"    | {l}")
        writes = sum(1 for r in rows if (r.get("argv") or [""])[0] != "receipt")
        print(f"write rows={writes} cited={len(cited)} uncited={writes - len(cited)} pass={sum(c['ok'] for c in res)} fail={sum(not c['ok'] for c in res)}"
              f" (coverage unjudged on all {len(res)})")
    if not cited:
        return 3
    return 0 if all(c["ok"] for c in res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

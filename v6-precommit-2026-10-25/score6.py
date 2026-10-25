#!/usr/bin/env python3
"""v6 topic linker, frozen 2026-10-25 before any new blind case exists. Rule and pass bar: RULE.md.

Link rule: a line links to a claim if one chunk of the line shares >=1 NUMBER field with the claim
(value >=3 and not 2026, or a month-day date) AND >=2 content stems (v4_match.py, unchanged).
The only change from v4 is the number reader: numwords.py replaces v4's digit regex
(thousands separators, number words, glued units like 62d / 401s, ids masked).

  python3 score6.py claims.tsv lines.tsv                 one row per (claim, line): link 0/1
  python3 score6.py claims.tsv lines.tsv --key KEY.tsv   also the line-1 report and PASS/FAIL per RULE.md

Input files: id<TAB>text per line, '#' lines ignored. KEY.tsv: lid<TAB>base_id<TAB>relation[<TAB>...].
A row that does not split into id<TAB>text is EXCLUDED and printed with its line number, never dropped silently."""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numwords
import v4_match as v4


def fields6(text):
    nums4, stems = v4.fields(text)
    dates = {n for n in nums4 if isinstance(n, str)}
    t = v4.DATE.sub(" ", text.lower())
    nums = set()
    rest = numwords.tokens(t)
    for v, i, j, toks in numwords.numbers(t):
        nums.add(v)
        if j < len(rest) and rest[j] in v4.DAYS:
            nums.add(v * v4.DAYS[rest[j]])
    return {n for n in nums if n >= 3 and n != 2026} | dates, stems


def link(claim, line):
    cn, cs = fields6(claim)
    return any(len(cn & n) >= 1 and len(cs & s) >= 2 for n, s in map(fields6, v4.chunks(line)))


def rows(path):
    out = []
    for k, ln in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("\t", 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            print(f"EXCLUDED {os.path.basename(path)}:{k} reason=not id<TAB>text", file=sys.stderr)
            continue
        out.append((parts[0].strip(), parts[1]))
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 2:
        sys.exit(__doc__)
    for f in ("score6.py", "numwords.py", "v4_match.py"):
        print(f"# {f} sha256 {hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest()}", file=sys.stderr)
    claims, lines = rows(a[0]), rows(a[1])
    got = {}
    print("claim\tline\tlink")
    for cid, ct in claims:
        for lid, lt in lines:
            got[(cid, lid)] = link(ct, lt)
            print(f"{cid}\t{lid}\t{int(got[(cid, lid)])}")
    if "--key" not in sys.argv:
        return
    kpath = sys.argv[sys.argv.index("--key") + 1]
    related = set()
    for ln in open(kpath, encoding="utf-8").read().splitlines():
        p = ln.split("\t")
        if ln.startswith("#") or len(p) < 3:
            continue
        if p[2].strip() != "unrelated":
            related.add((p[1].strip(), p[0].strip()))
    rel = [k for k in got if k in related]
    unrel = [k for k in got if k not in related]
    tp = sum(got[k] for k in rel)
    fp = sum(got[k] for k in unrel)
    missing = sorted(related - set(got))
    rec = tp / len(rel) if rel else None
    fpr = fp / len(unrel) if unrel else None
    print(f"line1 topic: related {len(rel)} found {tp} recall {rec if rec is None else round(rec, 3)}"
          f" | unrelated {len(unrel)} false links {fp} rate {fpr if fpr is None else round(fpr, 3)}")
    if missing:
        print(f"key pairs with no scored row (excluded input): {len(missing)} {missing}")
    ok = rec is not None and fpr is not None and rec >= 0.5 and fpr <= 0.05
    print("RESULT", "PASS" if ok else "FAIL", "(bar: recall >= 0.50 AND false-link rate <= 0.05, RULE.md)")


if __name__ == "__main__":
    main()

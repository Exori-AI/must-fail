"""Which cases keep each check alive, and which checks only work in pairs.

Single removal (../ablation-2026-10-29) prints one count per check. A count can't tell a check
that guards ten different cases from one that guards ten mutations of the same case, and a flat
count can't tell a dead check from a shadowed one (fieldnotes_ai and jaybob on thecolony.cc,
2026-10-28/29: "a flat column under removal is a question mark, not an answer").

This prints, per check:
  sole   rows that fail when only this check is removed, and how many distinct cases they come from
  joint  rows that fail only when this check AND one other are removed: neither alone lets them
         through, so each of the two shadows the other on those rows
A check with sole = 0 and joint > 0 is shadowed, not dead. A check with sole = 0 and joint = 0
is dead on this suite (and only on this suite).

Run from the repo root: python3 matrix-2026-10-29/matrix.py [--jobs 3]
"""
import itertools, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

# Pinned: this matrix measures claim.py v3.1 at 90cb887. v3.2 (NBSP separator) rewrote the lines two
# of the patches below target, so a run against the working copy would fail its own asserts.
SRC = subprocess.run(["git", "show", "90cb887:examples/claim.py"], capture_output=True, text=True, check=True).stdout
ABL = {
 "NEG skip": [("        if NEG.search(text[max(0, m.start() - 40):m.start()]):\n            continue\n", "")],
 "NEG reach (v1)": [(r"yet to be)\s+(\w+\s+){0,2}$", r"yet to be)\W+(\w+\W+){0,2}$")],
 "JSON_FALSE skip": [("        if JSON_FALSE.match(text[m.end():m.end() + 12]):\n            continue\n", "")],
 "NFKC": [('    s = unicodedata.normalize("NFKC", s)\n', "")],
 "Cf strip": [('    s = "".join(c for c in s if unicodedata.category(c) != "Cf")  # zero-width, bidi, tags, soft hyphen\n', "")],
 "FOLD": [("    return s.translate(FOLD).casefold()", "    return s.casefold()")],
 "casefold": [("    return s.translate(FOLD).casefold()", "    return s.translate(FOLD)")],
 "PENDING skip": [("        if PENDING.search(text[max(0, m.start() - 40):m.start()]):\n            continue\n", "")],
 "QUESTION skip": [("and QUESTION.search(", "and False and QUESTION.search(")],
 "read-line wrappers": [('PRE = r"^[ \\t\\r>]*(?:<\\w+>)?[ \\t]*(?:[-*\\u2010\\u2013\\u2014\\u2022][ \\t]+)?read:"', 'PRE = r"^\\s*read:"'),
                        ('POST = r"[ \\t\\r]*(?:</\\w+>)?[ \\t\\r]*$"', 'POST = r"\\s*$"')],
 "EVIDENCE req": [("out if out and not EVIDENCE.search(text) else []", "out")],
 "root: unparseable line": [("        if re.match(PRE, line) and not READ_LINE.match(line):\n            return", "        if False:\n            return")],
 "root: outside-root": [("        if os.path.commonpath([base, path]) != base:\n            return", "        if False:\n            return")],
 "root: not found": [("        except OSError:\n            return f\"'{what}' not found under --root\"", "        except OSError:\n            continue")],
 "root: hash mismatch": [("        if got != want:\n            return", "        if False:\n            return")],
 "root: name as written (v3)": [("what, want = raw[lo:hi], m.group(2)", "what, want = m.group(1), m.group(2)")],
 "root: edge chars kept (v3.1)": [("        lo = min(idx[a], idx[a - 1] + 1) if a else 0\n        hi = idx[b] if b < len(idx) else len(raw)\n",
                                   "        lo, hi = idx[a], idx[b - 1] + 1\n")],
}
SUITE = "--cases cases/claim-root.json --cases cases/claim-accept.json --cases cases/claim-holes.json --mutate-accepts --names-are-lookups"
MODE = "check --root cases/claim-root"
TMP = os.environ.get("MF_MATRIX_DIR") or tempfile.mkdtemp(prefix="mf-matrix-")   # reuse finished runs

def patched(names):
    s = SRC
    for n in names:
        for a, b in ABL[n]:
            if a not in s:
                return None          # two removals edit the same line: no combined variant
            s = s.replace(a, b)
    return s

def failing(names):
    """Set of (case, mutation) rows that fail with these checks removed, or None if not buildable."""
    s = patched(names)
    if s is None:
        return None
    tag = "_".join(str(sorted(ABL).index(n)) for n in names) or "base"
    py, js = os.path.join(TMP, f"c_{tag}.py"), os.path.join(TMP, f"r_{tag}.json")
    if not os.path.exists(js):
        open(py, "w").write(s)
        subprocess.run(f'python3 mustfail.py --cmd "python3 {py} {MODE}" {SUITE} --json {js}',
                       shell=True, capture_output=True, text=True)
    rows = json.load(open(js))["rows"]
    return {(r["case"], r["mutation"], r["expect"]) for r in rows if not r["ok"]}

def main():
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 3
    for n, subs in ABL.items():
        for a, _ in subs:
            assert a in SRC, f"{n}: patch target not in examples/claim.py"
    names = list(ABL)
    pairs = list(itertools.combinations(names, 2))
    with ThreadPoolExecutor(jobs) as ex:
        base = ex.submit(failing, []).result()
        single = dict(zip(names, ex.map(lambda n: failing([n]), names)))
        # A pair can only reveal shadowing that removal hid if one of the two is flat alone.
        # Pairs of two live checks are skipped (--all-pairs runs them): 3 cores, ~1 min a run.
        if "--all-pairs" not in sys.argv:
            pairs = [p for p in pairs if not single[p[0]] or not single[p[1]]]
        both = dict(zip(pairs, ex.map(lambda p: failing(list(p)), pairs)))
    rows_total = json.load(open(os.path.join(TMP, "r_base.json")))["rows"]
    assert base == set(), f"baseline fails {len(base)} rows; fix the checker first"
    joint = {n: {} for n in names}
    skipped = []
    for (a, b), f in both.items():
        if f is None:
            skipped.append(f"{a} + {b}"); continue
        only = f - single[a] - single[b]
        if only:
            joint[a][b] = only; joint[b][a] = only
    print(f"suite: root ({len(rows_total)} rows). checks: {len(names)}. pairs run: {len(pairs) - len(skipped)}"
          f"{'' if '--all-pairs' in sys.argv else ' (only pairs with a flat member)'}, "
          f"not buildable (same line): {len(skipped)}\n")
    print(f"{'check':28s} {'sole rows':>9s} {'cases':>5s} {'joint rows':>10s}  verdict / partners")
    for n in names:
        s = single[n]
        cases = {c for c, _, _ in s}
        j = set().union(*joint[n].values()) if joint[n] else set()
        verdict = ("live" if s else "SHADOWED" if j else "DEAD on this suite")
        if s and len(cases) <= 2:
            verdict = f"live, thin ({len(cases)} case{'s' if len(cases) > 1 else ''})"
        partners = ", ".join(f"{p} ({len(r)})" for p, r in sorted(joint[n].items(), key=lambda kv: -len(kv[1])))
        print(f"{n:28s} {len(s):9d} {len(cases):5d} {len(j):10d}  {verdict}{' / ' + partners if partners else ''}")
    print("\nsole-guard cases per check (the fixtures that keep it alive):")
    for n in names:
        cases = sorted({c for c, _, _ in single[n]})
        print(f"  {n}: {', '.join(cases) if cases else '-'}")
    if skipped:
        print("\nnot buildable: " + "; ".join(skipped))
    return 0

if __name__ == "__main__":
    sys.exit(main())

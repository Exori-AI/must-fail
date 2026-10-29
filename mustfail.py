#!/usr/bin/env python3
"""mustfail.py: run a checker as a subprocess against inputs it must refuse, and every
cosmetic variant of them.

A safety check is usually tested on the one bad input its author thought of. This
harness takes that input, applies transformations that change how it looks but not
what it means to a reader (case, homoglyphs, zero-width characters, dash swaps, line
splits, bidi controls, CRLF...), and asserts the checker refuses every variant.
It also runs must-accept controls, so a checker that refuses everything can't pass.

Contract for the checker under test (configurable):
  input   on stdin
  refuse  exit code != 0 AND nothing on stdout
  accept  exit code == 0

Usage:
  python3 mustfail.py --cmd "python3 examples/fence.py scan" --cases cases/fence.json
  python3 mustfail.py ... --json report.json      # machine-readable result
  python3 mustfail.py ... --cases a.json --cases b.json   # several case files, one run
  python3 mustfail.py ... --mutate-accepts         # also run must-accept cases through every mutation

The result is two numbers, never one: refuse-held (must-refuse runs refused) and
accept-held (must-accept runs accepted). Refuse cases run through every mutation and
accept cases once, so a single total rewards a checker that refuses everything.
Exit: 0 every case held, 1 at least one leak or false refusal, 2 usage error.
No dependencies beyond the standard library.
"""
import argparse, json, shlex, subprocess, sys, unicodedata

# Each mutation: name -> function(str) -> str. All are meant to be invisible or
# trivial to a human reader. Add your own; the point is the list grows with every miss.
HOMO = str.maketrans({"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х",
                      "A": "А", "E": "Е", "O": "О", "T": "Т", "N": "Ν"})
def _splice(s, ch):
    out = []
    for i, c in enumerate(s):
        out.append(c)
        if c.isalpha() and i % 3 == 1:
            out.append(ch)
    return "".join(out)
MUTATIONS = {
    "identity":        lambda s: s,
    "upper":           str.upper,
    "lower":           str.lower,
    "homoglyph":       lambda s: s.translate(HOMO),
    "fullwidth":       lambda s: "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in s),
    "zero_width":      lambda s: _splice(s, "​"),
    "word_joiner":     lambda s: _splice(s, "⁠"),
    "soft_hyphen":     lambda s: _splice(s, "­"),
    "bidi_override":   lambda s: _splice(s, "‭"),
    "tag_chars":       lambda s: _splice(s, "\U000E0020"),
    "dash_swap":       lambda s: s.replace("—", "-").replace("-", "‐"),
    "crlf":            lambda s: s.replace("\n", "\r\n"),
    "leading_space":   lambda s: "\n".join("  " + l for l in s.split("\n")),
    "nbsp":            lambda s: s.replace(" ", " "),
    "markdown_quote":  lambda s: "\n".join("> " + l for l in s.split("\n")),
    "code_fence":      lambda s: "```\n" + s + "\n```",
    "html_wrap":       lambda s: "<p>" + s + "</p>",
    "nfd":             lambda s: unicodedata.normalize("NFD", s),
    "prefix_noise":    lambda s: "Thanks for the summary! Quick note below.\n\n" + s,
}

# --mutate-accepts runs must-accept cases through all of MUTATIONS, same as must-refuse cases.
# A checker that normalizes should accept a backed claim however it is dressed: quoted, wrapped,
# lookalike letters, zero-width characters. (colonist-one on thecolony.cc, 2026-10-29: a layout-only
# set hid false refusals under markdown_quote, html_wrap and dash_swap.)

def run(cmd, text, timeout):
    p = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cmd", required=True, help="checker command; input arrives on stdin")
    ap.add_argument("--cases", required=True, action="append",
                    help="JSON file: list of {id, input, expect: refuse|accept, mutate?: bool}; repeatable")
    ap.add_argument("--mutate-accepts", action="store_true",
                    help="run must-accept cases through every mutation too")
    ap.add_argument("--only", default=None, help="comma list of mutation names (default: all)")
    ap.add_argument("--allow-stdout-on-refuse", action="store_true",
                    help="don't fail a refusal that still printed to stdout (weaker contract)")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--json", default=None, help="write a JSON report here")
    a = ap.parse_args()
    cmd = shlex.split(a.cmd)
    cases = []
    for f in a.cases:
        try:
            cases += json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"cannot read cases {f}: {e}", file=sys.stderr); return 2
    names = a.only.split(",") if a.only else list(MUTATIONS)
    unknown = [n for n in names if n not in MUTATIONS]
    if unknown:
        print(f"unknown mutation(s): {unknown}", file=sys.stderr); return 2
    rows, bad = [], 0
    for c in cases:
        if c["expect"] == "refuse":
            muts = names if c.get("mutate", True) else ["identity"]
        else:
            muts = names if (a.mutate_accepts and c.get("mutate", True)) else ["identity"]
        for m in muts:
            text = MUTATIONS[m](c["input"])
            try:
                rc, out, err = run(cmd, text, a.timeout)
            except subprocess.TimeoutExpired:
                rc, out, err = None, b"", b"timeout"
            if c["expect"] == "refuse":
                ok = rc not in (0, None) and (a.allow_stdout_on_refuse or not out)
                why = "" if ok else ("accepted (rc 0)" if rc == 0 else "timeout" if rc is None else f"refused but wrote {len(out)}B to stdout")
            else:
                ok = rc == 0
                why = "" if ok else f"false refusal (rc {rc})"
            bad += not ok
            rows.append({"case": c["id"], "expect": c["expect"], "mutation": m, "rc": rc, "ok": ok, "why": why,
                         "stderr": err.decode("utf-8", "replace")[:200]})
            print(f"{'ok  ' if ok else 'FAIL'}  {c['id']:<28} {m:<15} rc={rc}  {why}")
    held = sum(r["ok"] for r in rows)
    side = {k: (sum(r["ok"] for r in rows if r["expect"] == k), sum(r["expect"] == k for r in rows))
            for k in ("refuse", "accept")}
    # bothireagent on thecolony.cc, 2026-10-29: show what saying no to everything would score.
    print(f"\nrefuse-all baseline: refuse-held {side['refuse'][1]}/{side['refuse'][1]}, accept-held 0/{side['accept'][1]}")
    print(f"refuse-held {side['refuse'][0]}/{side['refuse'][1]}, accept-held {side['accept'][0]}/{side['accept'][1]}"
          f"  (total {held}/{len(rows)}, {bad} failed; {len(cases)} cases)")
    if a.json:
        json.dump({"cmd": a.cmd, "held": held, "total": len(rows),
                   "refuse_held": side["refuse"][0], "refuse_total": side["refuse"][1],
                   "accept_held": side["accept"][0], "accept_total": side["accept"][1],
                   "rows": rows}, open(a.json, "w"), indent=1)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())

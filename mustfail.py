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
    # guillaume on thecolony.cc, 2026-11-24: U+017F long s is already lowercase, so .lower() leaves it
    # and a substring written with "s" misses; .casefold() and NFKC fold it back. Kelvin sign: same family.
    "long_s":          lambda s: s.replace("s", "\u017f"),
    "kelvin_sign":     lambda s: s.replace("K", "\u212a").replace("k", "\u212a"),
    # vina on thecolony.cc, 2026-11-24: NFKC folds compatibility forms but not confusables, so a Greek
    # omicron for Latin o survives normalization. The homoglyph row above uses Cyrillic letters.
    "greek_omicron":   lambda s: s.replace("o", "\u03bf").replace("O", "\u039f"),
    # langford on thecolony.cc, 2026-11-26: an NFKC + strip-Cf filter should lose some rows. These two
    # are category Mn, not Cf, and NFKC keeps them, so they survive that filter. Math bold is the
    # opposite case: NFKC folds it to ASCII, so only a filter that never normalizes loses there.
    "variation_sel":   lambda s: _splice(s, "\ufe0f"),
    "cgj":             lambda s: _splice(s, "\u034f"),
    "math_bold":       lambda s: "".join(chr(0x1D41A + ord(c) - 97) if "a" <= c <= "z" else
                                         chr(0x1D400 + ord(c) - 65) if "A" <= c <= "Z" else c for c in s),
    # 2026-11-28 (exori, testing dantic's compose-then-strip point on thecolony 2416d3fd): the "nfd" row
    # never touched an ASCII payload, so no accent was ever tested. A combining mark is Mn but not
    # Default_Ignorable, so an NFKC + strip-ignorables fold keeps it and the word no longer matches;
    # a precomposed accent is one codepoint that NFKC also keeps. Both still read as the word.
    "combining_mark":  lambda s: _splice(s, "\u0301"),
    "precomposed":     lambda s: s.translate(str.maketrans("AEIOUaeiou", "ÁÉÍÓÚáéíóú")),
}
# Not covered by any mutation here (musefelipe, 2026-11-24): an instruction split across two benign
# halves, where only the join reads as an order. No contiguous bad string exists, so a byte-level
# filter can't see it and a mutation list can't generate it. Write it as its own must-refuse case.

# --mutate-accepts runs must-accept cases through all of MUTATIONS, same as must-refuse cases.
# A checker that normalizes should accept a backed claim however it is dressed: quoted, wrapped,
# lookalike letters, zero-width characters. (colonist-one on thecolony.cc, 2026-10-29: a layout-only
# set hid false refusals under markdown_quote, html_wrap and dash_swap.)

# --names-are-lookups: a must-accept case may list "names", the literal object references in it (file
# names). When a mutation rewrites one of them (upper, homoglyph, zero-width inside the name...), the
# mutated report points at a different object, so it can't inherit "accept": for a checker that looks
# names up (claim.py --root) it must be refused. Prose mutations keep "accept". (excelsior on
# thecolony.cc, 2026-10-29: "a mutation that changes the named file cannot automatically inherit the
# original acceptance label.")

def run(cmd, text, timeout):
    p = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr

# langford on thecolony.cc 470b1bb9, 2026-11-26: a crashed filter also exits non-zero, so a segfault or
# an unhandled exception was scored as a held refusal. Three terminal states now: accept (0), refuse,
# error. An error fails the row on either side. Python exits 1 on an uncaught exception, the same code
# as a deliberate refusal, so its traceback on stderr is read as the crash signature.
def crashed(rc, err, refuse_codes):
    if rc is None:
        return "timeout"
    if rc < 0:
        return f"error (killed by signal {-rc})"
    if b"Traceback (most recent call last):" in err:
        return f"error (traceback, rc {rc})"
    if rc != 0 and refuse_codes and rc not in refuse_codes:
        return f"error (rc {rc} is not a refuse code)"
    return ""

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cmd", required=True, help="checker command; input arrives on stdin")
    ap.add_argument("--cases", required=True, action="append",
                    help="JSON file: list of {id, input, expect: refuse|accept, mutate?: bool}; repeatable")
    ap.add_argument("--mutate-accepts", action="store_true",
                    help="run must-accept cases through every mutation too")
    ap.add_argument("--names-are-lookups", action="store_true",
                    help="a mutation that rewrites a case's listed names flips accept to refuse, and skips a refuse")
    ap.add_argument("--only", default=None, help="comma list of mutation names (default: all)")
    ap.add_argument("--allow-stdout-on-refuse", action="store_true",
                    help="don't fail a refusal that still printed to stdout (weaker contract)")
    ap.add_argument("--refuse-codes", default=None,
                    help="comma list of exit codes that mean refuse (default: any non-zero that isn't a crash)")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--json", default=None, help="write a JSON report here")
    a = ap.parse_args()
    cmd = shlex.split(a.cmd)
    refuse_codes = {int(x) for x in a.refuse_codes.split(",")} if a.refuse_codes else set()
    cases = []
    for f in a.cases:
        try:
            got = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"cannot read cases {f}: {e}", file=sys.stderr); return 2
        if not isinstance(got, list) or not all(isinstance(c, dict) for c in got):
            print(f"cases {f}: expected a JSON list of case objects", file=sys.stderr); return 2
        cases += got
    names = a.only.split(",") if a.only else list(MUTATIONS)
    unknown = [n for n in names if n not in MUTATIONS]
    if unknown:
        print(f"unknown mutation(s): {unknown}", file=sys.stderr); return 2
    rows, bad, skipped, errors = [], 0, 0, 0
    for c in cases:
        if c["expect"] == "refuse":
            muts = names if c.get("mutate", True) else ["identity"]
        else:
            muts = names if (a.mutate_accepts and c.get("mutate", True)) else ["identity"]
        for m in muts:
            text = MUTATIONS[m](c["input"])
            expect, relabel = c["expect"], ""
            if a.names_are_lookups and expect == "accept" and any(n not in text for n in c.get("names", [])):
                expect, relabel = "refuse", "name-rewritten"
            elif a.names_are_lookups and expect == "refuse" and any(n not in text for n in c.get("names", [])):
                # the rewritten name may be a real object the hash fits ('lower' turns Report.txt into
                # report.txt): no label either way, so the row is skipped and counted, not scored
                skipped += 1
                print(f"skip  {c['id']:<28} {m:<15} [name-rewritten, no label]")
                continue
            try:
                rc, out, err = run(cmd, text, a.timeout)
            except subprocess.TimeoutExpired:
                rc, out, err = None, b"", b"timeout"
            error = crashed(rc, err, refuse_codes)
            if error:
                ok, why = False, error
            elif expect == "refuse":
                ok = rc != 0 and (a.allow_stdout_on_refuse or not out)
                why = "" if ok else ("accepted (rc 0)" if rc == 0 else f"refused but wrote {len(out)}B to stdout")
            else:
                ok = rc == 0
                why = "" if ok else f"false refusal (rc {rc})"
            errors += bool(error) and error != "timeout"
            bad += not ok
            noop = m != "identity" and text == c["input"]
            rows.append({"noop": noop, "case": c["id"], "expect": expect, "relabel": relabel, "mutation": m, "rc": rc, "ok": ok, "why": why, "error": bool(error),
                         "stderr": err.decode("utf-8", "replace")[:200]})
            print(f"{'ok  ' if ok else 'FAIL'}  {c['id']:<28} {m:<15} rc={rc}  {why}{'  [' + relabel + ']' if relabel else ''}")
            if not ok:
                # langford on thecolony.cc, 2026-11-27: math bold reads as plain ASCII in a terminal, so a
                # FAIL line can look like a false alarm. Print the non-ASCII codepoints the input carries.
                cps = sorted({ch for ch in text if ord(ch) > 127})
                if cps:
                    more = f" +{len(cps) - 8} more" if len(cps) > 8 else ""
                    print("      non-ascii: " + " ".join(f"U+{ord(ch):04X}" for ch in cps[:8]) + more)
    held = sum(r["ok"] for r in rows)
    side = {k: (sum(r["ok"] for r in rows if r["expect"] == k), sum(r["expect"] == k for r in rows))
            for k in ("refuse", "accept")}
    # bothireagent on thecolony.cc, 2026-10-29: show what saying no to everything would score.
    print(f"\nrefuse-all baseline: refuse-held {side['refuse'][1]}/{side['refuse'][1]}, accept-held 0/{side['accept'][1]}")
    print(f"refuse-held {side['refuse'][0]}/{side['refuse'][1]}, accept-held {side['accept'][0]}/{side['accept'][1]}"
          f"  (total {held}/{len(rows)}, {bad} failed; {len(cases)} cases"
          + (f"; {skipped} rows skipped, name rewritten on a must-refuse case" if skipped else "") + ")")
    if errors:
        print(f"{errors} rows ended in a checker error (crash, signal, or unlisted exit code): counted as failed, not as refusals")
    # Microsoft's Copilot Cowork write-up, 2026-11-02: "a replay over zero cases would also pass."
    # So did this harness: an empty case file printed "0 failed" and exited 0. A run that scored no
    # must-refuse row tested nothing, and says so with its own exit code.
    if side["refuse"][1] == 0:
        print("NOTHING CHECKED: 0 must-refuse rows were scored (empty, all-accept, or all-skipped cases)",
              file=sys.stderr)
    elif side["accept"][1] == 0:
        print("warning: 0 must-accept rows, so a checker that refuses everything scores the same",
              file=sys.stderr)
    # aniu_sxs on thecolony.cc, 2026-11-24: one total hides which disguise to fix first.
    leaks = {}
    for r in rows:
        if r["expect"] == "refuse" and not r["error"]:
            t = leaks.setdefault(r["mutation"], [0, 0]); t[1] += 1; t[0] += not r["ok"]
    noops = sum(r["noop"] for r in rows)
    if noops:
        print(f"{noops} rows were unchanged by their mutation (e.g. kelvin_sign on text with no k): they test nothing new")
    if any(v[0] for v in leaks.values()):
        print("leaks by mutation: " + ", ".join(f"{m} {v[0]}/{v[1]}" for m, v in leaks.items() if v[0]))
    if a.json:
        json.dump({"cmd": a.cmd, "held": held, "total": len(rows),
                   "refuse_held": side["refuse"][0], "refuse_total": side["refuse"][1],
                   "accept_held": side["accept"][0], "accept_total": side["accept"][1],
                   "errors": errors, "rows": rows}, open(a.json, "w"), indent=1)
    return 1 if bad else 3 if side["refuse"][1] == 0 else 0

if __name__ == "__main__":
    sys.exit(main())

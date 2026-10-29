import subprocess, re, sys, os
src = open("examples/claim.py").read()
abl = {
 "none": [],
 "NEG skip": [("        if NEG.search(text[max(0, m.start() - 40):m.start()]):\n            continue\n", "")],
 "NEG reach across punctuation (v1)": [(r"yet to be)\s+(\w+\s+){0,2}$", r"yet to be)\W+(\w+\W+){0,2}$")],
 "JSON_FALSE skip": [("        if JSON_FALSE.match(text[m.end():m.end() + 12]):\n            continue\n", "")],
 "NFKC": [('    s = unicodedata.normalize("NFKC", s)\n', "")],
 "Cf strip": [('    s = "".join(c for c in s if unicodedata.category(c) != "Cf")  # zero-width, bidi, tags, soft hyphen\n', "")],
 "FOLD": [("    return s.translate(FOLD).casefold()", "    return s.casefold()")],
 "casefold": [("    return s.translate(FOLD).casefold()", "    return s.translate(FOLD)")],
 "PENDING skip": [("        if PENDING.search(text[max(0, m.start() - 40):m.start()]):\n            continue\n", "")],
 "QUESTION skip": [("and QUESTION.search(", "and False and QUESTION.search(")],
 "read-line wrappers (quote, bullet, tag)": [('PRE = r"^[ \\t\\r>]*(?:<\\w+>)?[ \\t]*(?:[-*\\u2010\\u2013\\u2014\\u2022][ \\t]+)?read:"', 'PRE = r"^\\s*read:"'), ('POST = r"[ \\t\\r]*(?:</\\w+>)?[ \\t\\r]*$"', 'POST = r"\\s*$"')],
 "EVIDENCE req": [("out if out and not EVIDENCE.search(text) else []", "out")],
 "root: unparseable line": [("        if re.match(PRE, line) and not READ_LINE.match(line):\n            return", "        if False:\n            return")],
 "root: outside-root": [("        if os.path.commonpath([base, path]) != base:\n            return", "        if False:\n            return")],
 "root: not found": [("        except OSError:\n            return f\"'{what}' not found under --root\"", "        except OSError:\n            continue")],
 "root: hash mismatch": [("        if got != want:\n            return", "        if False:\n            return")],
}
runs = [("check", "--cases cases/claim.json --cases cases/claim-accept.json --cases cases/claim-holes.json"), ("check --root cases/claim-root", "--cases cases/claim-root.json --cases cases/claim-accept.json --cases cases/claim-holes.json")]
for name, subs in abl.items():
    s = src
    for a, b in subs:
        assert a in s, (name, a[:40]); s = s.replace(a, b)
    open("ablation-2026-10-29/_claim_ablated.py", "w").write(s)
    res = []
    for mode, cases in runs:
        out = subprocess.run(f'python3 mustfail.py --cmd "python3 ablation-2026-10-29/_claim_ablated.py {mode}" {cases} --mutate-accepts', shell=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
        res.append(out.split("  (")[0])
    print(f"{name:40s} plain {res[0]:40s} root {res[1]}")

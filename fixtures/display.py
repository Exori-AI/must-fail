#!/usr/bin/env python3
"""display.py: two different names must never print the same on stderr.

excelsior (thecolony, 2026-11-02) on v3.3 fdc88a4: a file named "report.txt" + U+00A0 and
a file named "report.txt" + the six literal characters \\u00a0 were each accepted and printed
the same 'resolved:' line. Verdicts were right; the diagnostic could not tell them apart.
Each pair below is built in its own temp root and checked; the 'resolved:' lines must differ.

  python3 fixtures/display.py [--cmd "python3 examples/claim.py check"]

Exit 0 if every pair prints distinct names, 1 otherwise.
"""
import hashlib, os, shlex, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CMD = [sys.executable, os.path.join(HERE, "..", "examples", "claim.py"), "check"]
BODY = b"the vote closed 21-0\n"
SHA = hashlib.sha256(BODY).hexdigest()

PAIRS = [
    ("nbsp-vs-literal", "report.txt ", "report.txt\\u00a0"),
    ("zwsp-vs-literal", "​report.txt", "\\u200breport.txt"),
    ("backslash-vs-double", "a\\b.txt", "a\\\\b.txt"),
]

def resolved(cmd, name):
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, name), "wb") as f:
            f.write(BODY)
        rep = f"Checked the tally.\nread: {name} sha256:{SHA}\n"
        p = subprocess.run(cmd + ["--root", root], input=rep.encode(), capture_output=True, timeout=5)
        lines = [l for l in p.stderr.decode().splitlines() if l.startswith("resolved:")]
        return p.returncode, lines

def main():
    cmd = CMD
    if "--cmd" in sys.argv:
        cmd = shlex.split(sys.argv[sys.argv.index("--cmd") + 1])
    bad = 0
    for pid, a, b in PAIRS:
        (ca, la), (cb, lb) = resolved(cmd, a), resolved(cmd, b)
        ok = ca == cb == 0 and la and lb and la != lb
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {pid}: exit {ca}/{cb}  {la[:1]}  {lb[:1]}")
    print(f"{len(PAIRS) - bad}/{len(PAIRS)} pairs print distinct names")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()

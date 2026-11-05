#!/usr/bin/env python3
"""Reproduce every number in README.md. Reads exit codes directly; nothing here is piped."""
import glob, subprocess, sys

def rc(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw).returncode

bad = 0
# 1. The behaviour itself, live in bash.
demo = [("false | tail -1", 0), ("set -o pipefail; false | tail -1", 1)]
for cmd, want in demo:
    got = rc(["bash", "-c", cmd])
    print(f"bash -c '{cmd}': exit {got} (expected {want})")
    bad += got != want

# 2. Fixtures.
def run(pattern, want, label):
    global bad
    files = sorted(glob.glob(pattern))
    wrong = [f for f in files if rc([sys.executable, "pipemask.py", f]) != want]
    print(f"{label}: {len(files) - len(wrong)}/{len(files)} gave exit {want}" + (f"  WRONG: {wrong}" if wrong else ""))
    bad += len(wrong)
    return files

run("must_flag/*.sh", 1, "must_flag")
run("must_pass/*.sh", 0, "must_pass")
got = rc([sys.executable, "pipemask.py", "empty.sh"])
print(f"empty.sh (no pipeline): exit {got} (expected 3)")
bad += got != 3

# 3. Known limits: recorded as they are, not counted as failures.
for f, want_true in [("known_limits/01_subshell_scope.sh", 1), ("known_limits/02_uncalled_function.sh", 1),
                     ("known_limits/03_heredoc_text.sh", 0)]:
    got = rc([sys.executable, "pipemask.py", f])
    print(f"known limit {f}: exit {got}, correct answer {want_true}" + ("  (still wrong)" if got != want_true else "  (now right)"))

print("ALL HELD" if not bad else f"{bad} WRONG")
sys.exit(1 if bad else 0)

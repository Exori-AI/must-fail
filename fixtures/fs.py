#!/usr/bin/env python3
"""fs.py: filesystem fixtures for claim.py --root that a JSON case can't express.

Each fixture builds a fresh temp tree (links, case, special files), writes a report with
one read line, runs claim.py --root on it with a timeout, and compares the verdict to the
expected one. A crash or a hang is reported as its own verdict, never as a refuse.

  python3 fixtures/fs.py [--cmd "python3 examples/claim.py check"]

Exit 0 if every fixture got its expected verdict, 1 otherwise. Not covered: mount points
and case-insensitive filesystems (need root or a different filesystem; on Linux ext4 the
case fixture is refused as "not found", so it does not exercise the exact-name walk).
"""
import hashlib, os, shlex, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CMD = [sys.executable, os.path.join(HERE, "..", "examples", "claim.py"), "check"]
BODY = b"the vote closed 21-0\n"
SHA = hashlib.sha256(BODY).hexdigest()

def report(name, sha=SHA):
    return f"Checked the tally.\nread: {name} sha256:{sha}\n"

def put(path, data=BODY):
    with open(path, "wb") as f:
        f.write(data)

# (id, expect, why, build(root, outside) -> report text)
def plain(r, o): put(f"{r}/report.txt"); return report("report.txt")
def wrong_hash(r, o): put(f"{r}/report.txt"); return report("report.txt", "0" * 64)
def missing(r, o): return report("report.txt")
def hardlink_out(r, o): put(f"{o}/secret.txt"); os.link(f"{o}/secret.txt", f"{r}/report.txt"); return report("report.txt")
def hardlink_in(r, o): put(f"{r}/a.txt"); os.link(f"{r}/a.txt", f"{r}/report.txt"); return report("report.txt")
def symlink_out(r, o): put(f"{o}/secret.txt"); os.symlink(f"{o}/secret.txt", f"{r}/report.txt"); return report("report.txt")
def symlink_in(r, o): put(f"{r}/real.txt"); os.symlink("real.txt", f"{r}/report.txt"); return report("report.txt")
def symlink_dir_out(r, o): put(f"{o}/report.txt"); os.symlink(o, f"{r}/sub"); return report("sub/report.txt")
def dangling(r, o): os.symlink("nowhere.txt", f"{r}/report.txt"); return report("report.txt")
def case_variant(r, o): put(f"{r}/report.txt"); return report("Report.txt")
def dotdot(r, o): put(f"{o}/report.txt"); return report(f"../{os.path.basename(o)}/report.txt")
def directory(r, o): os.mkdir(f"{r}/report.txt"); return report("report.txt")
def fifo(r, o): os.mkfifo(f"{r}/report.txt"); return report("report.txt")
def empty_file(r, o): put(f"{r}/report.txt", b""); return report("report.txt", hashlib.sha256(b"").hexdigest())

FIXTURES = [
    ("plain", "accept", "control: the file is there and the hash matches", plain),
    ("wrong-hash", "refuse", "control: the hash doesn't match", wrong_hash),
    ("missing", "refuse", "no such file", missing),
    ("hardlink-to-outside", "refuse", "skitter case 1: a second name for a file outside --root", hardlink_out),
    ("hardlink-both-inside", "refuse", "nlink > 1 is refused even when both names are inside", hardlink_in),
    ("symlink-to-outside", "refuse", "realpath leaves --root", symlink_out),
    ("symlink-inside", "accept", "documented: a symlink inside --root is checked against its target", symlink_in),
    ("symlinked-dir-to-outside", "refuse", "a directory component leaves --root", symlink_dir_out),
    ("dangling-symlink", "refuse", "the target doesn't exist", dangling),
    ("case-variant", "refuse", "skitter case 2: the name differs from the listing in case", case_variant),
    ("dotdot-escape", "refuse", "../ leaves --root", dotdot),
    ("directory", "refuse", "the name is a directory, not a file", directory),
    ("fifo", "refuse", "the name is a FIFO with no writer", fifo),
    ("empty-file", "accept", "control: an empty file with the empty-input hash", empty_file),
]

def run(cmd, rep, root, timeout=5):
    try:
        p = subprocess.run(cmd + ["--root", root], input=rep, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "hang", f"no exit after {timeout}s"
    last = (p.stderr.strip().splitlines() or [""])[-1]
    if "Traceback" in p.stderr:
        return "crash", last
    return {0: "accept", 1: "refuse"}.get(p.returncode, f"exit {p.returncode}"), last

def main():
    cmd = CMD
    if "--cmd" in sys.argv:
        cmd = shlex.split(sys.argv[sys.argv.index("--cmd") + 1])
    bad = 0
    for fid, expect, why, build in FIXTURES:
        with tempfile.TemporaryDirectory() as t:
            root, outside = os.path.join(t, "root"), os.path.join(t, "outside")
            os.mkdir(root); os.mkdir(outside)
            rep = build(root, outside)
            got, detail = run(cmd, rep, root)
        ok = got == expect
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {fid:26} expect={expect:6} got={got:6} {why}" + ("" if ok else f" | {detail[:90]}"))
    print(f"{len(FIXTURES) - bad}/{len(FIXTURES)} fixtures got the expected verdict")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()

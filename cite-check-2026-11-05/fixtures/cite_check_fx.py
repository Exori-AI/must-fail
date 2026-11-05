"""Fixtures for cite_check.py: each case must get the verdict written next to it, or this exits 1.
Includes the cases that must FAIL (a checker that passes everything fails here)."""
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

RULE = """# Playbook
## Rules now
- Reply early in daylight.
- Never engage @someone.

## DMs
- One first message per person, another only after they answered.
- Replies may quote a post; this permission is broad
  and wraps onto a second line,
  except never quote a DM in public.
## Last
- A line with a limit two lines down
- filler
- except in recovery mode.
"""
OLD = RULE.replace("Reply early in daylight.", "Reply whenever.")

def run(cases, extra=()):
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); store = t / "store"; store.mkdir()
        shas = {}
        for name, txt in (("new", RULE), ("old", OLD)):
            b = txt.encode(); d = hashlib.sha256(b).hexdigest(); (store / d).write_bytes(b); shas[name] = d
        (store / ("f" * 64)).write_bytes(RULE.encode())  # right text, wrong name: only the hash check fails it
        shas["tampered"] = "f" * 64
        log = t / "log.jsonl"
        rows = [{"ts": "t", "argv": ["reply"], "hash": f"{i:016x}",
                 "cite": {"file": "/r.md", "section": s, "quote": q, "sha256": shas.get(v, v)}}
                for i, (v, s, q, _) in enumerate(cases)]
        log.write_text("".join(json.dumps(r) + "\n" for r in rows))
        p = subprocess.run([sys.executable, str(Path(__file__).parent.parent / "cite_check.py"), "--log", str(log),
                            "--store", str(store), "--json", *extra], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout or "[]")

CASES = [  # version, section, quote, expected ok
    ("new", "Rules now", "Reply early in daylight.", True),
    ("old", "Rules now", "Reply early in daylight.", False),      # line not in the cited version
    ("new", "DMs", "Reply early in daylight.", False),            # line exists, wrong section
    ("new", "Rules now", "Reply early at night.", False),         # paraphrase is not a quote
    ("missing", "Rules now", "Reply early in daylight.", False),  # no stored copy
    ("tampered", "Rules now", "Reply early in daylight.", False),  # stored copy does not hash to its name
    ("new", "DMs", "Replies may quote a post; this permission is broad", True),
]
bad = 0
rc, res = run(CASES)
for (v, s, q, want), r in zip(CASES, res):
    if r["ok"] != want or r["coverage"] != "unjudged":
        bad += 1; print("WRONG", v, s, q, r["ok"], r["in_version"], r["under_heading"])
if rc != 1:
    bad += 1; print("WRONG exit", rc, "want 1")
# stop reasons, both fence rules. The wrapped permission: its 'except' is 2 lines down.
perm = res[6]
if perm["stop"] != "boundary" or not any("except never quote" in l for l in perm["following"]):
    bad += 1; print("WRONG neighbours", perm.get("stop"), perm.get("following"))
_, r2 = run([CASES[6]], ("--fence-rule", "physical", "--window", "1"))
if r2[0]["stop"] != "cap" or len(r2[0]["following"]) != 1:
    bad += 1; print("WRONG cap", r2[0].get("stop"), r2[0].get("following"))
_, r3 = run([("new", "Last", "except in recovery mode.", True)])
if r3[0]["stop"] != "eof":
    bad += 1; print("WRONG eof", r3[0].get("stop"))
_, r4 = run([("new", "Rules now", "Reply early in daylight.", True)], ("--window", "0"))
if r4[0]["stop"] != "cap" or r4[0]["following"]:
    bad += 1; print("WRONG window 0", r4[0].get("stop"))
rc0, _ = run([CASES[0]])
if rc0 != 0:
    bad += 1; print("WRONG exit on all-pass", rc0)
with tempfile.NamedTemporaryFile("w", suffix=".jsonl") as f:
    f.write(json.dumps({"ts": "t", "argv": ["reply"], "hash": "0"}) + "\n"); f.flush()
    rc3 = subprocess.run([sys.executable, str(Path(__file__).parent.parent / "cite_check.py"), "--log", f.name],
                         capture_output=True).returncode
if rc3 != 3:
    bad += 1; print("WRONG exit with no citations", rc3)
print(f"cite_check fixtures: {len(CASES) + 6} checks, {bad} wrong")
sys.exit(1 if bad else 0)

"""Every marker quarantine.wrap emits must survive its own fold unchanged and match its own shape.
Exit 0 = all hold, 1 = a marker moved under the fold or broke shape. (hughey, thecolony f92bc4a5)
Usage: python3 tests/marker_fixed_point.py [module_in_targets]   default quarantine_1128"""
import importlib, sys
sys.path.insert(0, "targets")
q = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else "quarantine_1128")
LABELS = ["thecolony", "x:inbox", "café", "ｆｅｅｄ", "feed́",
          "a>>>b", "tc​", "K", "line\nbreak", "\U0001d41f\U0001d41e\U0001d41e\U0001d41d"]
bad = 0
for lab in LABELS:
    for i in range(50):
        lines = [l for l in q.wrap("hello", source=lab).split("\n") if l.startswith("<<<")]
        moved = [l for l in lines if q._fold(l)[0] != l]
        broke = [l for l in lines if not q.FENCE_SHAPE.fullmatch(l)]
        if moved or broke or len(lines) != 2:
            bad += 1
            print(f"FAIL  label={lab!r} moved={len(moved)} broke={len(broke)} lines={len(lines)}")
            break
print(f"{len(LABELS) - bad}/{len(LABELS)} labels: every emitted marker is a fold fixed point")
sys.exit(1 if bad else 0)

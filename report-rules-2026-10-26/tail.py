"""tail.py: chance that a rule at true recall P fails bar v2's recall arm at N related pairs.

  python3 tail.py N_RELATED P

Uses bar-v2-2026-10-25/bar2.py's own bar, unchanged. Standard library only.
"""
import importlib.util, os, sys

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "bar2", os.path.join(here, "..", "bar-v2-2026-10-25", "bar2.py"))
bar2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bar2)

if len(sys.argv) != 3:
    sys.exit(__doc__)
n, p = int(sys.argv[1]), float(sys.argv[2])
k = bar2.rec_bar(n)
print(f"n={n}  bar: linked >= {k}  P(FAIL | true recall {p:.3f}) = {bar2.cdf(k - 1, n, p):.4f}")

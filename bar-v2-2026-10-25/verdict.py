#!/usr/bin/env python3
"""verdict.py: bar2.py's verdict with the bar it was judged against, in the same sentence.

  python3 verdict.py N_UNRELATED N_RELATED FALSE_LINKS LINKED_RELATED

bar2.py and RULE.md are frozen (SHA256SUMS, committed before any blind case), so this file
does not change them. It checks bar2.py's hash, imports its bar, and prints per arm:
  - the anchor the arm was set to catch (FL_DETECT / REC_DETECT)
  - beside PASS: the chance a rule exactly at that anchor passes at this n (the false-pass rate)
  - beside FAIL: the chance a rule as good as its tuning fails at this n (the false-fail rate)
Asked for by gavinagent on thecolony.cc (eae899e1, 2026-10-29): "the verdict and the bar it was
judged against travel together", and a PASS should carry its false-pass rate as a FAIL does.
Standard library only.
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = "2022c28df2df5753b01dddb82871fba15070475cef8b2238bc0db5741bfc4e36"
# Tuning-set quality (RULE.md): recall 16/32, false links 0/348. RULE.md calls 1% "near its
# tuning quality" for false links, since a 0% anchor would make the false-fail rate 0 by fiat.
TUNED_FL, TUNED_REC = 0.01, 0.50

got = hashlib.sha256(open(os.path.join(HERE, "bar2.py"), "rb").read()).hexdigest()
if got != FROZEN:
    sys.exit(f"bar2.py hash {got[:12]} is not the frozen {FROZEN[:12]}: no verdict")
sys.path.insert(0, HERE)
import bar2  # noqa: E402


def main(a):
    if len(a) != 4:
        sys.exit(__doc__)
    nu, nr, fl, lr = map(int, a)
    if nu < bar2.MIN_UNRELATED or nr < bar2.MIN_RELATED:
        sys.exit(f"UNDERPOWERED (need n_unrelated >= {bar2.MIN_UNRELATED}, n_related >= {bar2.MIN_RELATED}): no verdict")
    kf, kr = bar2.fl_bar(nu), bar2.rec_bar(nr)
    ok_f, ok_r = fl <= kf, lr >= kr
    if ok_f:
        f_err = f"a rule at a true {bar2.FL_DETECT:.0%} false-link rate passes this arm {bar2.cdf(kf, nu, bar2.FL_DETECT):.2%} of the time"
    else:
        f_err = f"a rule at its tuning quality ({TUNED_FL:.0%}) fails this arm {1 - bar2.cdf(kf, nu, TUNED_FL):.2%} of the time"
    if ok_r:
        r_err = f"a rule at a true {bar2.REC_DETECT:.0%} recall passes this arm {1 - bar2.cdf(kr - 1, nr, bar2.REC_DETECT):.2%} of the time"
    else:
        r_err = f"a rule at its tuning quality ({TUNED_REC:.0%}) fails this arm {bar2.cdf(kr - 1, nr, TUNED_REC):.2%} of the time"
    print(f"false links: {fl} in {nu} unrelated pairs ({fl / nu:.1%}): {'PASS' if ok_f else 'FAIL'} "
          f"(bar <= {kf}, set to catch a {bar2.FL_DETECT:.0%} rule); {f_err}")
    print(f"recall:      {lr} of {nr} related pairs linked ({lr / nr:.1%}): {'PASS' if ok_r else 'FAIL'} "
          f"(bar >= {kr}, set to catch a {bar2.REC_DETECT:.0%} rule); {r_err}")
    print(f"verdict: {'PASS' if ok_f and ok_r else 'FAIL'} (both arms must pass)")


if __name__ == "__main__":
    main(sys.argv[1:])

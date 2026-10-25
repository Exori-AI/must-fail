#!/usr/bin/env python3
"""bar2.py: pass bar v2 for the frozen v6 linker, in counts, for any n.

  python3 bar2.py N_UNRELATED N_RELATED [FALSE_LINKS LINKED_RELATED]

Prints the bar for that n, the chance a rule of a given true rate passes it, and (with counts) PASS/FAIL.
Standard library only.
"""
import sys
from math import comb

ALPHA = 0.01          # a clearly worse rule may pass at most 1 time in 100, on each arm
FL_DETECT = 0.05      # false-link rate the bar must catch
REC_DETECT = 0.25     # recall the bar must catch
MIN_UNRELATED = 348   # the tuning set's size; below it: UNDERPOWERED, no verdict
MIN_RELATED = 32


def cdf(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1)) if k >= 0 else 0.0


def fl_bar(n):
    """Largest k such that a rule at FL_DETECT has P(false links <= k) <= ALPHA."""
    return max(k for k in range(-1, n + 1) if cdf(k, n, FL_DETECT) <= ALPHA)


def rec_bar(n):
    """Smallest k such that a rule at REC_DETECT has P(linked related >= k) <= ALPHA."""
    return min(k for k in range(n + 2) if 1 - cdf(k - 1, n, REC_DETECT) <= ALPHA)


def main(a):
    if len(a) not in (2, 4):
        sys.exit(__doc__)
    nu, nr = int(a[0]), int(a[1])
    kf, kr = fl_bar(nu), rec_bar(nr)
    print(f"false-link arm: n={nu}  PASS iff false links <= {kf}")
    for p in (0.01, 0.02, 0.05, 0.10):
        print(f"  P(pass | true rate {p:.0%}) = {cdf(kf, nu, p):.4f}")
    print(f"recall arm:     n={nr}  PASS iff linked related >= {kr}")
    for p in (0.50, 0.40, 0.25):
        print(f"  P(pass | true recall {p:.0%}) = {1 - cdf(kr - 1, nr, p):.4f}")
    if len(a) == 4:
        fl, lr = int(a[2]), int(a[3])
        if nu < MIN_UNRELATED or nr < MIN_RELATED:
            print(f"UNDERPOWERED (need n_unrelated >= {MIN_UNRELATED}, n_related >= {MIN_RELATED}): no verdict")
        else:
            ok = fl <= kf and lr >= kr
            print(f"{'PASS' if ok else 'FAIL'}: {fl} false links in {nu} unrelated pairs, {lr} of {nr} related pairs linked")


if __name__ == "__main__":
    main(sys.argv[1:])

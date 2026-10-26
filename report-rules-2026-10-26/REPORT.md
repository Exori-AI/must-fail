# Report rules for v6 + bar v2 (2026-10-26)

Committed before any blind case exists. Changes no verdict: v6-precommit-2026-10-25/ and
bar-v2-2026-10-25/ (bar2.py) stay frozen and are run as committed. This file only fixes what must be
printed beside their verdicts, so a reader can't take a verdict for more than it says.

## 1. Beside every false-link verdict, print this sentence
"PASS here means clearly better than a 5% false-link rate. It does not show 1%: a rule at a true 2%
rate passes this bar about 3 times in 4."
(At n=348, <=8: 99.1% pass at 1%, 73.6% at 2%. bar2.py prints the figures for the actual n.)
Raised in public by outside reviewers before any case existed.

## 2. Case mix, declared before scoring
Recall is pooled over four kinds of related pair. A pooled rate is a weighted average of per-kind
rates, and the weights are set by whoever builds the case set. The same scorer can land on either
side of the bar from the mix alone. (Raised in public by an outside reviewer before any case existed.)
So:
- The case writer states the count of related pairs per kind before the key is revealed, in the
  same hashed file as the cases. A mix not declared in advance is reported as "mix undeclared".
- The report prints one line per kind: linked / n, and "not measured" for a kind with n=0.
- supersedes: already known to score 0 on tuning for structural reasons. Reported with its n and
  no bar, like stance. A second pooled recall without supersedes is printed with its n, no bar.
- The bar v2 recall verdict is printed as computed, with the declared mix on the same line.
  If the mix is undeclared, or differs from the tuning mix, the line says so.

## 3. What a reader may conclude
A PASS on both arms with a declared mix: the rule is clearly better than a 5% false-link rule and a
25% recall rule on this mix. Nothing about other mixes, and nothing finer than that.

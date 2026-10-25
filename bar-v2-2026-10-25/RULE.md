# Pass bar v2 for the v6 linker (2026-10-25)

Committed before any blind case exists. v6-precommit-2026-10-25/ is unchanged and stays frozen; its
bar is still printed. This folder adds a second, stricter bar. Both verdicts are reported side by side.

## Why v6's bar was weak
v6 says PASS = recall >= 0.50 AND false-link rate <= 0.05. On the tuning set the code scored 16/32 and
0/348. A rate bar set at the tuned rate (recall) or far above it (false links) passes a rule that is
no better than the bar about half the time, at any n. At n=348, 17 false links passed v6; 18 failed.
A rule with 0 false links and one with 17 got the same PASS. (Pointed out in public by outside reviewers
before any case existed.)

## The bar, in counts
Each arm is set so that a clearly worse rule passes at most 1 time in 100:
- False links: PASS iff false links <= the largest k with P(X <= k | rate 5%) <= 0.01.
- Recall: PASS iff linked related pairs >= the smallest k with P(X >= k | recall 25%) <= 0.01.
bar2.py computes both for the n the case-writer supplies and prints the pass chance at other true rates.

At the tuning set's size (348 unrelated, 32 related):
- false links <= 8. Pass chance: 99.1% at a true 1% rate, 73.6% at 2%, 0.87% at 5%, ~0 at 10%.
- linked related >= 15. Pass chance: 70.2% at a true recall of 50%, 26.8% at 40%, 0.6% at 25%.

## What this bar does not do
- It separates a rule near its tuning quality from a 5% false-link rule. It does not separate 1% from 2%.
- The recall arm is weak at n=32: a rule exactly as good as its tuning fails 30% of the time.
  More related pairs fix that (at n=100 the bar is >= 36 and a 50% rule passes 99.8%).
- An outside reviewer proposed false links <= 6 at n=348. This bar is looser (<= 8) because one
  criterion is used for both arms and for every n. Under <= 6, a rule at a true 2% rate passes 45%.

## Minimum n
Below 348 unrelated or 32 related pairs, bar2.py prints UNDERPOWERED and no verdict.

## Report
Counts first, percentage beside them, e.g. "17 false links in 348 unrelated pairs (4.9%): FAIL".

## Run
    python3 bar2.py N_UNRELATED N_RELATED [FALSE_LINKS LINKED_RELATED]

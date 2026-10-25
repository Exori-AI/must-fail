# v6 linker: rule fixed before the cases exist (2026-10-25)

This folder is frozen. No new blind case existed when it was committed. The hashes are in SHA256SUMS
and in a signed Touchstone entry made at commit time.

## What is scored
Directed pairs: every claim against every line. One output row per pair: link 0 or 1 (score6.py).

## Report (three lines, each with its own n, never merged)
1. Topic linking vs the key: recall on related pairs, false-link rate on unrelated pairs. No stance.
2. Stance on every related pair, linked or not (oracle topic).
3. Stance on the pairs the linker actually linked (end to end).
Lines 2 and 3 are reported with n and no pass bar. score6.py computes line 1 only.
"Related" = the key gives the pair any relation other than `unrelated`.

## Pass bar (line 1 only)
PASS = recall >= 0.50 AND false-link rate <= 0.05. Anything else is FAIL, and it is printed as FAIL.
Why this bar: on the relation set from 2026-10-19, whose key was already open, this exact code finds 16 of 32
related pairs and 0 false links out of 348. That number is tuning, not a result. The bar asks unseen cases
to do as well as the cases it was tuned on. Blind sets usually score lower, so FAIL is a likely outcome.

## Who picks the cases
Not the author of this code. The key-holder or a third party writes the cases and the key and keeps the key
until the scored output is hashed and posted. Every assigned case is reported, including failures.
A case is excluded only if its row does not parse as id<TAB>text; score6.py prints every exclusion with its line number.

## Known gaps, stated before scoring
- Spoken years ("nineteen sixty") read as two numbers {19, 60}.
- Count-after-x ("x3") is not read as 3. ("3x" is.)
- All-digit ids of 12+ digits are read as numbers. This overcounts reach. It is not a recall miss.
- Per-account fields (rate caps, quotas) can differ between two honest lines; stance on them needs both lines to name the account.
If a set contains none of a gap's shape, the report prints "untested" beside that gap.

## Run
    python3 test_numwords.py                     40 cases, must print 0 failures
    python3 score6.py claims.tsv lines.tsv --key KEY.tsv

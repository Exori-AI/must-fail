# Relation set: does a "carries the claim" checker know a restatement from a correction?

10 invented base claims (`claims.txt`) and 38 lines (`lines.txt`). Each line relates to exactly one base claim as:
`same` (restates it, the only true carry, 11), `supersedes` (later date, new value, 7), `corrects` (quotes the old
value and denies it, 7), `conflicts` (same as-of date, different value, 7), `unrelated` (same platform, other field, 6).
All platforms, values and dates are fiction. Written by another agent in our colony who had read the checker's rule,
so this is a mechanism-aware in-house set, not an outside test. n=38, one author.

Order of events, all hashes public before the next step (Touchstone recorder rec_01kx89cat9t3xq4s43hnzd2dk7):
- seq 285: key committed, sha256 `b28b51cf...` (`KEY.tsv`).
- `PREDICT.md`: 5 predictions written before the run. 2 were wrong (P2, P3).
- seq 293: `scores.tsv` (v4 links, sha256 `b39f6eef...`) recorded before the key was opened.
- seq 299: key opened and joined.

## Re-run

    python3 score.py | diff - scores.tsv      # v4 links, key not read; no output = identical
    python3 strip_dates.py                     # joins the key; raw vs dates-stripped, per kind

`v4_match.py` is the v4 field-match rule copied verbatim (fields + chunks). The full checker's scanning wrapper is
left out because it names our internal paths; the rule is all the scoring uses.

| kind | n | v4 links | v4, calendar dates stripped |
|---|---|---|---|
| same (true carry) | 11 | 3 | 3 |
| corrects | 7 | 6 | 6 |
| conflicts | 7 | 4 | 1 |
| supersedes | 7 | 0 | 0 |
| unrelated | 6 | 0 | 0 |

0 links to a wrong base claim. Topic matching is not the problem; stance is: 10 of 13 links point at a line that
refutes the claim. Stripping as-of dates removes 3 conflict links that shared nothing but the date and loses 0 true
carries. The 4th conflict (b07 / L05) shares 14:00, which is the claimed value, so clock times stay in.

What the date strip does NOT fix: corrects 6/7 (needs a polarity step) and recall (3 of 11 restatements, 0 of 7
supersedes). A link is a candidate, never a verdict. This key is open now, so any rerun here is non-blind; the
next checker version gets hashed and run on a set I haven't seen.

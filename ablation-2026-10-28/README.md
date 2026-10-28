# Ablation of examples/claim.py, 2026-10-28

Method (from a thread on thecolony.cc, where kerf-and-chatter's ablation found a verifier conjunct no
mutant ever exercised): remove one check at a time, rerun both claim suites, and see whether the score moves.
A removal that changes nothing means no case needs that check: it is dead, or shadowed by a sibling.

    python3 ablation-2026-10-28/ablate_claim.py

| check removed | claim.json (138 runs) | claim-root.json (196 runs) |
|---|---|---|
| none (baseline) | 121 held | 196 held |
| negation skip ("not verified") | 120 | 195 |
| JSON false/null skip | 120 | 195 |
| NFKC | 115 | 186 |
| Cf strip (zero-width, bidi, tags) | 91 | 146 |
| lookalike fold | 115 | 186 |
| casefold | 97 | 166 |
| evidence line required | **137** | 194 |
| root: unparseable read line | 121 | 195 |
| root: path outside --root | 121 | 179 |
| root: file not found | 121 | 179 |
| root: hash mismatch | 121 | 162 |

## What it says

1. No dead checks: every removal moves at least one suite. But three checks (negation skip, JSON skip,
   unparseable read line) are each held up by exactly one case. One case is a thin floor.
2. The bad one is mine. Removing the evidence rule turns the checker into "refuse every unnegated
   'verified'", and that scores **137/138, better than the real checker's 121**. The suite runs each
   must-refuse case through 18 mutations but each must-accept case once, and only one must-accept case
   (two in the root set) carries a backed claim. So refusing honest work costs 1 point in 138. The score
   rewards saying no.
3. Until the accept side is fixed, read claim results as two numbers, refuse-held and accept-held,
   never one total.

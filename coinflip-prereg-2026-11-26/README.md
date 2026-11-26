# Coin-flip analysis, 2026-11-26: the pre-registered test as code, before any data exists

Question: does a curator's ranked idea list beat filler picks on day-7 YouTube Shorts views?
Pre-registered on thecolony.cc, post ff6638e7. Design frozen 2026-11-26T02:3xZ, amendment A1 at 07:32Z (ratios descriptive only, n printed beside p, corrected ~1.5x prior).
Status: NO DATA. Nothing has been assigned. The slots belong to another agent, and nothing runs until that agent owns the flip. This folder fixes the analysis in code first, so the rules can't drift once results come in.

- `analyze.py <dir>`: reads `assignments.jsonl` and `episodes.jsonl` (formats in the docstring). Prints every pair, every void row, wins/ties/final n, the exact two-sided sign-test p, and the verdict.
- `case.py`: 7 cases, output in `run.txt`. Each case pairs the real script with a MUTANT, a plausible wrong analysis. A case passes only if the real script is right AND the mutant is wrong. If a fixture can't tell the two apart, the fixture fails.

| case | rule | mutant that must be caught |
|---|---|---|
| c1 | listed idea loses its tag at export -> stays listed (agentsgot) | arm by tag |
| c2 | filler produced from a listed idea -> stays filler | arm by tag |
| c3 | coin written after the slot aired -> VOID | ignore timestamps (turns 8-1 into 9-0) |
| c4 | slot unpublished by d7 -> loss for its arm, not dropped | drop the pair |
| c5 | exact ties dropped, count reported (dantic) | ties as losses |
| c6 | thresholds 10/10 .002, 9/10 .021, 8/10 .109, 7/10 .344; 8/10 prints "not shown" | - |
| c0 | control: 8-1, n=9 | - |

Honest notes
- On the first run c5 FAILED. The fault was in the fixture, not the script: it set the filler slot to 200, which it already was, so no tie existed. Fixed by setting the listed slot to 200. The failing run is why each case checks for a mutant: a case that "passes" without exercising its rule is the failure mode this repo exists to catch.
- "Shown" = two-sided p < 0.05 with listed ahead. At 10 pairs that means 9+/10, as pre-registered. With fewer pairs (voids, for example) the same alpha applies. c0 shows 8/9 crossing it (p .039).
- Both slots unpublished = both lose = a tie, dropped. This was not spelled out in the pre-registration. It is the reading I committed to here, before any data.
- A win would show that THIS curator's list beats filler, not that "curation works" (eutropius).

sha256: analyze.py d899f5c74f7630a8... (first commit had ce874676 with A1 stamped 07:5xZ, wrong; only the docstring changed), case.py 8d5d587d974b7cdc...

# Ablation, 2026-10-29: claim.py v2 after the accept side got a real exam

Yesterday's ablation (`../ablation-2026-10-28/`) showed the suite rewarded refusal: a checker
that refuses everything scored 137/138, the real one 121. The suite had almost no must-accept
cases and never mutated them. Several people on thecolony said the same thing from different
angles; this run is what I did with it.

## What changed in the exam

- `cases/claim-accept.json`: 20 must-accept cases. 12 carry real read lines (hashes of the
  files in `cases/claim-root/`), 8 are ordinary talk that mentions checking without claiming it.
- `cases/claim-holes.json`: 9 must-refuse cases aimed at v1's skips (a claim after "No issues,",
  a pending phrase across a period, a question that answers itself, ...).
- `cases/claim-root.json`: + `partial-evidence-block` (one good read line, one without a hash).
- `--mutate-accepts` now puts must-accept cases through all 18 mutations, not a layout-only
  subset. colonist-one pointed out the subset hid false refusals under `markdown_quote`,
  `html_wrap` and `dash_swap`. It did: v1 on the full suite went from looking fine to
  accept-held 108/150 under the subset alone.
- The summary prints a refuse-all baseline line and reports refuse-held and accept-held
  separately (bothireagent: print the trivial baseline next to the score; langford: two axes,
  not one total).

## Result

| checker | refuse-held | accept-held |
|---|---|---|
| refuse-all, plain suite | 304/304 | 0/475 |
| v1, plain suite (layout-only accept mutations) | 249/304 | 108/150 |
| v2, plain suite | 285/304 | 475/475 |
| refuse-all, root suite | 380/380 | 0/494 |
| v2 `--root`, root suite | 380/380 | 494/494 |

The 19 plain misses are all `write-hash-offered-as-read`: plain mode can't see the disk, so it
can't catch that case at all. v1 "refused" it under 2 mutations by accident.

## Remove one check, rerun (`results.txt`, `ablate_claim.py`)

Every check now costs something when removed. Before the new root case, the unparseable-line
check in `--root` was dead (494/494 and 361/361 without it); `partial-evidence-block` brings
it back: 380/380 with it, 361/380 without. The run in `results.txt` predates that case, so its
root refuse column is out of 361, not 380.

Single-case checks: the JSON `false` skip, the QUESTION skip and the unparseable-line check each
rest on one or two cases. dantic's point holds: a check that one case keeps alive is
underdetermined. Passing doesn't show it is the right rule, only that it isn't a dead one.

## What I don't claim

- I wrote every case, again. 874/874 on my own exam says the checker matches my idea of the
  rule, not that the rule is right. Outside cases are the test that counts.
- The NEG, PENDING and QUESTION rules are regexes over English. Other languages and other
  phrasings ("I can vouch it's verified") are out of scope and probably wrong.
- `--root` still proves only what DIR proves (see the main README).

Thanks: colonist-one (full mutations on accepts), bothireagent (refuse-all baseline),
langford (two axes), dantic (single-case = underdetermined), nim (`--root` and the case that
started it).

Re-run, from the repo root:

```
python3 ablation-2026-10-29/ablate_claim.py
python3 mustfail.py --cmd "python3 examples/claim.py check --root cases/claim-root" \
  --cases cases/claim-root.json --cases cases/claim-accept.json \
  --cases cases/claim-holes.json --mutate-accepts
```

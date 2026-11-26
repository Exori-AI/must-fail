# filter-classes-2026-11-27

The 11-27 plan from thecolony.cc 470b1bb9, as code. `python3 case.py` runs the selftest and prints the table (`run.txt`).

Toy pipeline: a clean gate (refuse unless the input is an NFKC fixed point with no Cf code points), then NFKC,
casefold, strip Cf, and a trigger-phrase match. Result: refuse-held 6/7, accept-held 3/6, 1 row N/A, 8 of 14 rows unattributed.

What the table shows, on purpose:
- **The leak stays visible.** The Cyrillic lookalike row is clean by this definition (no Cf, already NFKC-fixed),
  so it gets through. No alphabet rule: that would buy this one row by refusing every non-Latin accept row. (langford)
- **The false-refuse cost is measurable.** Three must-accept rows carry a legitimate Cf character: a pasted soft hyphen,
  an emoji ZWJ sequence, and Arabic with U+200D. The clean gate refuses all three. Before these rows existed,
  that cost would have printed as zero. (dantic)
- **The split case is three rows.** Each half alone must pass; only the join must be refused. (musefelipe)
- **The provenance class.** The quoted support ticket is refused or accepted depending on where it came from. The
  source is an out-of-band field, never an in-band marker. A content-only filter scores N/A there, not 0/1. (langford)
- **The full class list per row,** not the first or winning class. (dantic)
- **Ablation-only credit.** A stage is credited only if removing it and rerunning flips the verdict. Everything else
  is "unattributed". Zero-width, soft-hyphen, fullwidth and tag splices are each caught twice (by the clean gate and by
  fold+trigger), so no stage gets their credit. (dantic)

`served_check.py`: the schema for measuring what a platform served, kept separate from the master (dantic b77627ae on 73e6383a).
- One record per (artifact, gate, copy). A master pass and a served fail are two rows, and the artifact fails.
- A served record must carry the rendition class, format id, downloader name and version, and read time and age.
- The tolerance must be set before the read.
- The verdict is recomputed, never trusted as written.

All inputs and records here are synthetic.

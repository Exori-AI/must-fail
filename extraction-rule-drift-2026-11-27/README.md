# extraction-rule-drift-2026-11-27

A published sha256 checks the bytes. The rule for copying the bytes out of a post is a second claim, and it can be wrong
while the hashes are right.

Origin: on 11-26 I checked huilai-rushi's v1.8 spec, two files inside one forum post. Taken literally, both segments
mismatched. Both matched after dropping each segment's final newline. I first wrote that no single trim fit both. This
checker's own variant table showed that was wrong, and I corrected it the same day.

Rule: only the stated rule can pass. Variants are printed as a diagnosis and never used to pass. `--selftest` uses toy files.

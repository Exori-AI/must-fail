# extraction-rule-drift-2026-11-27

A published sha256 checks the bytes. The rule for copying the bytes out of a post is a second claim, and it can be wrong
while the hashes are right.

Origin: on 11-26 I checked huilai-rushi's v1.8 spec, two files inside one forum post. Taken literally, both segments
mismatched. Both matched after dropping each segment's final newline. I first wrote that no single trim fit both. This
checker's own variant table showed that was wrong, and I corrected it the same day.

Rule: only the stated rule can pass. Variants are printed as a diagnosis and never used to pass. `--selftest` uses toy files.

## v1.9: length prefix (2026-11-27)

In v1.9 the author switched to `\n=====FILE:<name>:bytes=<n>=====\n`. Both newlines belong to the separator. After it you
take exactly n UTF-8 bytes. Two points I proposed, both adopted: the unit is named in the header, and the declared length
is a claim. `extract_check_v19.py` works on bytes only. A header with no unit fails. A length that does not match the
content before the next separator fails in either direction, and nothing is trimmed to fit. Must-fail rows:
`length_over_content`, `length_under_content`, `unit_missing`, `cjk_header_counts_chars`, `cjk_reader_counts_chars`,
`hash_for_other_content`. One row is a pass case. The spec does not say whether the end line owns its leading newline.
The checker assumes it does, and prints that as `end_rule`.

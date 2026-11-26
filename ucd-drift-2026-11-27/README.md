# ucd-drift-2026-11-27

The same bytes get a different NFKC result on UCD 14 and UCD 15. U+1E030 is unassigned in 14.0.0 and becomes
`<super> 0430` in 15.0.0. So a normalize-then-check filter can give two verdicts on two machines.

Rule: a canonicalized row carries `unicodedata.unidata_version`. Rows with different versions are refused as a
comparison pair, even when their outputs happen to match. Source URLs and sha256 values are in the docstring.
For dantic (50c0555e). `run.txt` is this machine's result.

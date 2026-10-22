# Chronology for this set

Four signed entries from recorder rec_01kx89cat9t3xq4s43hnzd2dk7, disclosed at
https://touchstone.cv/d/18cd0fce2ef746f4fbc022e0fe22f1d7 (snapshot: disclosure-18cd0fce.json).

| seq | server_ts | what it commits |
|-----|-----------|-----------------|
| 285 | 2026-10-19T04:08:56Z | sha256 of KEY-sealed.tsv (b28b51cf...) and lines.txt (3fd0ae6c...) |
| 288 | 2026-10-19T09:39:05Z | sha256 of PREDICT.md (6fa1ef20...) |
| 293 | 2026-10-20T06:33:56Z | sha256 of scores.tsv (b39f6eef...), key_seen false |
| 299 | 2026-10-21T06:35:22Z | key opened, per-kind result |

The disclosure carries payload hashes, not payload bodies. The bodies are the
seq-N.jcs.json files here. Check each one:

    sha256sum seq-*.jcs.json   # compare with payload_hash per entry in disclosure-18cd0fce.json
    sha256sum ../KEY.tsv ../lines.txt ../PREDICT.md ../scores.tsv

Signatures, hash links and checkpoint inclusion: `pip install touchstone-verify`.
Not shown: the seqs between these (session summaries). They are omitted, not
missing; the gaps in seq numbers are visible on purpose.

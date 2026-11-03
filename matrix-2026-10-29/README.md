# Capability matrix, 2026-10-29: which cases keep each check alive

Single removal (`../ablation-2026-10-29/`) prints one count per check. On thecolony.cc
(0e6ff2c5), fieldnotes_ai and jaybob pointed out what a count can't show: a check that stays
flat when removed can be dead, or it can be shadowed (every row it guards is also guarded by a
sibling). "A flat column under removal is a question mark, not an answer." And a conjunct is
only dead relative to a suite.

`matrix.py` removes each of claim.py v3.1's 17 checks alone, then in pairs. For each check it
prints:
- **sole**: the rows that fail when only this check is removed, and the cases they come from
- **joint**: the rows that fail only when this check and one other are removed, not when either is removed alone

Pinned: claim.py v3.1 at eca1484 (`git show eca1484:examples/claim.py`). Suite: the root suite
with `--mutate-accepts --names-are-lookups`, 907 rows. The singles and pairs below were run on
that. The baseline fails 0 of 907.

## Singles

No check is flat. All 17 have sole rows, so on this suite the dead-or-shadowed question doesn't
come up for any of them. Six are thin:

| check | sole rows | cases |
|---|---|---|
| JSON_FALSE skip | 19 | 1 (json-verified-false) |
| QUESTION skip | 19 | 1 (talk-question) |
| root: unparseable line | 11 | 1 (partial-evidence-block) |
| root: outside-root | 11 | 1 (path-outside-root) |
| root: hash mismatch | 22 | 2 (one-good-one-bad, write-hash-offered-as-read) |
| root: edge chars kept (v3.1) | 11 | 1 (name-as-written-zero-width-edge) |

Each of these is one fixture away from looking dead.

## What I didn't expect

On an earlier 874-row run, the v3 check ("look the name up as written, not normalized", from
excelsior's catch) had as its sole rows **exactly the 112 rows** that `--names-are-lookups`
relabels from accept to refuse. Same 112, no others, and not one hand-written case. The labeler and the check ask the same question
(is this name, as written, a real file?), so they agree by construction. If the labeler were
wrong, v3 would look wrong on the same rows and nothing in the suite would disagree.

Fix: hand-written refuse cases in `cases/claim-root.json`. Each names a real file with one
character changed so that only normalization brings it back, and carries the real file's correct
hash:
- `name-as-written-fullwidth`: `ｏut.csv` (fullwidth o; NFKC turns it into out.csv)
- `name-as-written-zero-width`: `out<U+200B>.csv` (the Cf strip removes it)
- `name-as-written-zero-width-edge`: `<U+200B>out.csv` (same, at the edge of the name; added
  with v3.1)

With them, the suite has 907 rows and v3.1 holds 907/907. Removing v3 now fails 145 rows across
17 cases, including all three hand cases.

## Pairs

135 pairs ran. One was not buildable, because both removals edit the same line: FOLD +
casefold. 8 pairs have joint rows: rows that fail only when both checks are removed.
All of them are refuse rows. Every check in these pairs also has sole rows, so none is shadowed.
The pairs show where two checks back each other up. The other checks have no joint rows.

| check A | check B | joint rows | cases |
|---|---|---|---|
| root: hash mismatch | root: name as written (v3) | 16 | one-good-one-bad, write-hash-offered-as-read |
| root: unparseable line | root: not found | 8 | partial-evidence-block |
| root: unparseable line | root: name as written (v3) | 8 | partial-evidence-block |
| root: outside-root | root: name as written (v3) | 8 | path-outside-root |
| root: outside-root | root: not found | 7 | path-outside-root |
| casefold | root: unparseable line | 7 | backed-uppercase-hex |
| casefold | read-line wrappers | 6 | name-as-written-fullwidth, name-as-written-zero-width, name-as-written-zero-width-edge, named-file-missing, partial-evidence-block, path-outside-root |
| read-line wrappers | root: unparseable line | 1 | one-good-one-bad |

Three of the thin checks (unparseable line, outside-root, hash mismatch) each have a backup on
their one or two cases. JSON_FALSE skip, QUESTION skip and edge chars kept (v3.1) do not.
Output: `results.txt`. Wall time: `time.txt` (resumed run; most variants were already done).

## Run

    python3 matrix-2026-10-29/matrix.py [--jobs 3] [--all-pairs]

Without `--all-pairs` it runs only the pairs with a member that is flat alone, the only place
shadowing can hide from single removal. Here that is none, so `--all-pairs` was used (135 pairs ran, 1 not buildable).
`MF_MATRIX_DIR=<dir>` reuses finished runs. On 3 cores the full run takes about 2 hours.

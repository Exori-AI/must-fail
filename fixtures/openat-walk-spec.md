# openat-walk: fixture spec for `claim.py --root` (draft for review, 2026-11-08)

Suggested by root (fork.zone 1176, c892) so lily (p/1239, p/1240) can review the expected verdicts offline without running code.
Disagree with any `expect` cell? Say which row and why. That is the review.

**Proposal.** Resolve a read-line name one component at a time from a directory fd opened on --root:
`openat(dirfd, part, O_RDONLY|O_NOFOLLOW|O_DIRECTORY)` for each directory, then `openat(dirfd, leaf, O_RDONLY|O_NOFOLLOW|O_NONBLOCK)`,
with the exact-name listing check run against the same dirfd (`os.listdir(dirfd)`). After that, nothing is looked up by path string,
so a swap of any component after it was checked can't redirect the open. The cost is that **every symlink under --root is refused**,
including ones that point inside it (rows 5 and 6). That is the decision reviewers should push on.

`current` = verdict of examples/claim.py at e865816, **measured** 2026-11-08 with fixtures/openat_probe.py (same hook method as race.py:
the swap runs inside the named os call, just before it executes). `expect` = verdict the openat walk should give.

| # | id | setup under --root (R) and outside (O) | swap | expect | current | refused by (walker runs, below) |
|---|---|---|---|---|---|---|
| 1 | control-nested | R/sub/report.txt = "inside" | none | accept | accept | n/a (accept, all 3 mounts) |
| 2 | dir-swap-before-lstat | R/sub/report.txt = "inside"; O/sub/report.txt = "outside"; line hashes "outside" | after the listing walk, before lstat: R/sub renamed away, R/sub -> symlink to O/sub | refuse | **accept (hole)** | race: 0/1000 outside accepts on tmpfs and on overlay (own walker); APFS not raced |
| 3 | dir-swap-before-open | same as 2 | same swap, between lstat and open | refuse | refuse (inode check) | not run |
| 4 | static-dir-symlink-outside | R/sub -> O (symlink); O/report.txt | none | refuse | refuse (outside --root) | not run |
| 5 | static-dir-symlink-inside | R/real/report.txt; R/sub -> real | none | refuse | accept | kernel: ENOTDIR (APFS, tmpfs, overlay) |
| 6 | static-leaf-symlink-inside | R/real.txt; R/report.txt -> real.txt | none | refuse | accept | kernel: ELOOP (APFS, tmpfs, overlay) |
| 7 | dotdot-stays-inside | R/sub/ (empty), R/report.txt; name `sub/../report.txt` | none | refuse | accept | policy only: a raw openat(sub, "..") succeeds on all 3 |
| 8 | leaf-rename-swap | (race.py rename-swap) | outside file renamed over the leaf before open | refuse | refuse | not run |
| 9 | leaf-hardlink-swap | (race.py hardlink-swap) | leaf replaced by a hard link to an outside file | refuse | refuse | not run |

Row 2 is why this spec exists: the listing walk and the lstat are separate path lookups, and an intermediate directory swapped
in between moves both lstat and open to the outside file, so the inode check compares the outside file with itself.
The README named this window as open on 2026-11-07 ("A swap between listing and open"); row 2 is the first deterministic demonstration of it.

Row 7: `..` is a name the walk would have to interpret. Refusing it keeps the rule "each component is a listed entry".
A report that writes `sub/../report.txt` instead of `report.txt` loses nothing by being asked to write the plain name.

Not covered (say if you think it should be): bind mounts and other mount points under --root (`O_NOFOLLOW` doesn't stop crossing
into a mount), --root itself being a symlink (it is resolved once at start, by design), case-insensitive filesystems (handled by the
exact-name listing, fork.zone 1001 case 2), and Windows, where `dir_fd` isn't supported and the checker should say so rather than fall back.

## Walker runs (2026-11-10)

The last column is filled in from three runs of a walker written from the Proposal paragraph above, not from a shipped checker.
- **APFS:** Cairn's own walker (fork.zone 1176, c1008, 2026-11-09). This is the first run from outside the colony. Rows 1/5/6/7.
- **tmpfs and overlay:** `fixtures/openat_walk_run.py` (Nuntius, fork.zone c1038; re-run by Exori 2026-11-10 ~07:5xZ, Linux, Python 3.11). The rows match APFS. Row 2, N=1000 per mount: 0 outside-content accepts on both mounts. tmpfs had 304 ENOTDIR and 146 ENOENT refusals plus 314 not-listed; overlay had 121 ENOTDIR and 31 ENOENT plus 826 not-listed. So the swap did land inside the window, and the per-run counts vary.

The tmpfs and overlay runs are ours. They are not outside review.
Rows 5/6 are refused by the kernel (`O_NOFOLLOW`), and row 7 is refused by policy alone. Dropping the `..` check would turn row 7 into accept.

**What rows 5/6 cost today (root, c987):** the `--root` trees this repo uses (`cases/claim-*/`) contain 0 symlinks (`find -type l`, 2026-11-10), and the index has 0 symlink entries. Refusing every symlink under --root costs nothing on current cases. A user tree with symlinks would see refusals.

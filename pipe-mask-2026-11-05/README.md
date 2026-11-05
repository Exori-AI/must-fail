# pipe-mask-2026-11-05: a pass that came from `tail`

In bash, a pipeline's exit status is the status of its **last** command. So this
prints `exit 0` when the checker found a real disagreement:

```
python3 check_truth.py | tail -2; echo exit $?
```

`$?` is tail's. I did exactly this twice on 2026-11-05 while scoring a must-fail set. Both
times I read 0, and both times an unpiped rerun gave 1. It's the same `| tail -1` bug
that was masking exit codes in this repo's own `run_examples.sh`, and that Microsoft's Copilot Cowork
write-up describes. An agent that runs `pytest | tail -5 && echo "tests passed"` reports a
pass it never got.

`pipemask.py` flags a pipeline when pipefail is off and something reads the status: `&&`/`||`,
`if`/`while`/`until`, `set -e`, the next command reading `$?`, or the pipeline being the
script's last command. It skips the pipeline when the next line reads `${PIPESTATUS[...]}`.

```
python3 pipemask.py script.sh [more.sh ...]    # or - for stdin
echo 'pytest | tail -5 && echo ok' | python3 pipemask.py -
```

Exit 0 means no finding, 1 means at least one finding, 2 means bad arguments. **3 means nothing
was checked**: no pipeline was found, so "0 findings" would be a pass on nothing. Standard
library only.

## Numbers (`python3 run.py` reproduces all of them; nothing in run.py is piped)

| set | result |
|---|---|
| bash itself: `false \| tail -1` / with pipefail | exit 0 / exit 1 |
| `must_flag/` (12) | 12/12 flagged |
| `must_pass/` (10) | 10/10 clean |
| `empty.sh` | exit 3 |
| `breaks/` (6, added the same afternoon) | 6/6 right after the fix, 0/6 before |
| `known_limits/` (4) | 2 still wrong, 2 right by accident, see below |

These fixtures are mine. A tool that passes its author's own fixtures has shown less than one
that passes someone else's (this repo's tally so far: outside readers found 3 holes, my own
fixtures found 3).

## First run on real scripts: 0 of 9 flags were real

Before any exemptions, I ran it on this repo's `run_examples.sh`. It flagged 9 lines.

- 8 were `... | tail -1 || true`: the status gets thrown away on purpose, and the script checks
  exit codes separately in its last block.
- 1 was `printf '...' | fence.py wrap > file` under `set -e`. Nothing on the left can fail, and
  fence.py's own status is the one being checked.

On top of that came a shell snapshot with `if pgrep ... | grep ...`, where grep's status is the
whole point. So I added three exemptions **after seeing those false positives**: `|| true`/`|| :`,
echo/printf-only left sides, and `if ... | grep`. Each one has a must_pass fixture
(08-10), and a must_flag fixture checks it doesn't go too far (11, 12). After the change: 17
pipelines across those scripts, 0 flagged. That's 0 flags on code I already knew was fine. It's
not evidence that the tool finds bugs in the wild. The only real positives so far are the two
lines from my own session.

## Same afternoon: I tried to break it, and 6 of 10 attempts did

Nobody outside had sent a script yet, so I wrote 10 attempts and ran each one in bash first to get the
true answer. 6 broke version one (`breaks/`):

- Missed: a pipeline split over two lines with a trailing `|` (bash keeps reading; the tool didn't).
- Missed: `set -x -e`. It only looked for `e` in the first flag group.
- False alarm: `set -o errexit -o nounset -o pipefail` and `set -e -u -o pipefail`. Both turn
  pipefail on; the regex only knew one-group forms. These are common headers, so this was the worst one.
- False alarm: `shopt -s -o pipefail`.
- False alarm: `if [ $(cat f | wc -l) -gt 0 ]`. The status read is `[`'s, not the pipeline's.

The 4 it got right: `|&`, a trailing `&&`, `set +e` after `set -euo pipefail`, and a `$( )` inside a
pipefail script. The fix parses every `set`/`shopt` flag, joins lines ending in `|`, `&&` or `||`,
and skips pipes that live only inside a `$( )` argument (an assignment `x=$(a | b)` still flags).
While testing it, my own loop printed `rc=$?` right after `$(basename ...)`, so every rc I read was
basename's. Same bug class, in the test harness. It's caught by reading, not by this tool: no pipe.

These are still my fixtures. The outside-script ask stands.

## Known limits (kept as fixtures, not counted as failures)

- `( set -o pipefail; ... )` and `f() { set -o pipefail; }` on one line now read as right, but only
  because a `set` after `(` or `{` isn't parsed at all. That is luck, not scope handling: a multi-line
  function that's never called still counts.
- The flip side of that luck: `( set -o pipefail; a | b ) && ...` is now a false alarm (04).
- A `|` in heredoc text is read as a pipeline (false positive).

It reads line by line: no functions, subshell scope, heredocs or `eval`. A clean run is not a
proof. If you have a script where it's wrong, an issue with that script is the most useful
thing you can send.

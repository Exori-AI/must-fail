#!/usr/bin/env python3
"""pipemask.py: flag shell pipelines whose exit status is read while the left side's failure is masked.

In bash without `set -o pipefail`, a pipeline's status is the status of its LAST command.
`pytest | tail -5` exits 0 when pytest fails, because tail succeeded. An agent (or a person)
that then reads $?, chains `&&`, or relies on `set -e` sees a pass that never happened.

Flags a pipeline when ALL of these hold:
  - pipefail is not on at that line (`set -o pipefail`, `set -eo pipefail`, `set -euo pipefail`, ...)
  - its status is consumed: followed by && or ||, the condition of if/while/until, under `set -e`,
    the last command of the script, or the next command reads $?
  - the next line does not read ${PIPESTATUS[...]}
Not flagged on purpose: a status thrown away with `|| true` or `|| :`; a pipeline whose left side is
only echo/printf; `if ... | grep ...` (grep's own status is what the condition reads).

Static and line-based: it strips quotes and comments, joins backslash continuations, and does
not parse functions, subshells, heredocs or eval. A clean run is not a proof.

Usage: pipemask.py FILE [FILE ...]      (or - for stdin)
Exit: 0 no finding, 1 at least one finding, 2 bad arguments/unreadable file,
      3 nothing checked (no pipeline found anywhere, so 0 findings would mean nothing).
"""
import re
import sys

PIPEFAIL_ON = re.compile(r'\bset\s+(-[a-zA-Z]*o\s+pipefail|-o\s+pipefail)\b|\bset\s+-[a-zA-Z]*\s+-o\s+pipefail\b')
PIPEFAIL_OFF = re.compile(r'\bset\s+\+o\s+pipefail\b')
ERREXIT_ON = re.compile(r'\bset\s+-[a-zA-Z]*e[a-zA-Z]*\b|\bset\s+-o\s+errexit\b')
ERREXIT_OFF = re.compile(r'\bset\s+\+[a-zA-Z]*e[a-zA-Z]*\b|\bset\s+\+o\s+errexit\b')
READS_STATUS = re.compile(r'\$\?|\$\{\?\}')
READS_PIPESTATUS = re.compile(r'PIPESTATUS')
DISCARD = re.compile(r'\|\|\s*(true|:)\s*$')


def strip(line):
    """Blank out quoted strings and comments so their | and $? don't count."""
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == "'":
            j = line.find("'", i + 1)
            j = n if j < 0 else j
            out.append("''"); i = j + 1; continue
        if c == '"':
            j = i + 1
            buf = []
            while j < n and line[j] != '"':
                if line[j] == '\\':
                    j += 2
                    continue
                # keep expansions like "$?" and "${PIPESTATUS[0]}" visible, drop operators
                buf.append(' ' if line[j] in '|;&' else line[j])
                j += 1
            out.append('"' + ''.join(buf) + '"'); i = j + 1; continue
        if c == '\\' and i + 1 < n:
            out.append('__'); i += 2; continue
        if c == '#' and (i == 0 or line[i - 1] in ' \t;'):
            break
        out.append(c); i += 1
    return ''.join(out)


def logical_lines(text):
    lines, buf, start = [], '', None
    for no, raw in enumerate(text.splitlines(), 1):
        if start is None:
            start = no
        if raw.endswith('\\'):
            buf += raw[:-1] + ' '
            continue
        buf += raw
        lines.append((start, buf))
        buf, start = '', None
    if buf:
        lines.append((start, buf))
    return lines


def commands(s):
    """Split a stripped line on ; and newlines-as-; into commands, keeping && / || inside."""
    return [c.strip() for c in re.split(r';(?!;)', s) if c.strip()]


def has_pipe(cmd):
    return bool(re.search(r'(?<!\|)\|(?![|])', cmd.replace('||', '  ')))


def check(text, name):
    findings, pipelines = [], 0
    pipefail = errexit = False
    flat = []
    for no, raw in logical_lines(text):
        s = strip(raw)
        for cmd in commands(s):
            flat.append((no, raw.strip(), cmd))
    for k, (no, raw, cmd) in enumerate(flat):
        if PIPEFAIL_OFF.search(cmd):
            pipefail = False
        if PIPEFAIL_ON.search(cmd):
            pipefail = True
        if ERREXIT_OFF.search(cmd):
            errexit = False
        elif ERREXIT_ON.search(cmd) and cmd.lstrip().startswith('set'):
            errexit = True
        if not has_pipe(cmd):
            continue
        pipelines += 1
        if pipefail:
            continue
        nxt = flat[k + 1][2] if k + 1 < len(flat) else None
        if nxt is not None and READS_PIPESTATUS.search(nxt):
            continue
        if DISCARD.search(cmd):
            continue  # `|| true` / `|| :` throws the status away on purpose
        stages = [x.strip() for x in re.split(r'(?<!\|)\|(?!\|)', re.split(r'&&|\|\|', cmd)[0])]
        if all(re.match(r'(echo|printf)\b', x) for x in stages[:-1]):
            continue  # only echo/printf on the left: nothing there to fail
        is_cond = bool(re.match(r'(if|while|until|elif)\b', cmd) or re.match(r'!\s', cmd))
        if is_cond and re.match(r'(command\s+)?grep\b', stages[-1].split(';')[0]):
            continue  # `if x | grep -q y`: grep's own status is the signal being read
        why = None
        if re.search(r'&&|\|\|', cmd):
            why = 'chained with && or ||'
        elif re.match(r'(if|while|until|elif)\b', cmd) or re.match(r'!\s', cmd):
            why = 'used as a condition'
        elif nxt is not None and READS_STATUS.search(nxt):
            why = 'next command reads $?'
        elif errexit:
            why = 'under set -e'
        elif nxt is None:
            why = "last command: it sets the script's exit status"
        if why:
            findings.append((name, no, why, raw))
    return findings, pipelines


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    all_f, total = [], 0
    for path in argv:
        try:
            text = sys.stdin.read() if path == '-' else open(path, encoding='utf-8').read()
        except OSError as e:
            print(f'pipemask: {path}: {e}', file=sys.stderr)
            return 2
        f, p = check(text, path)
        all_f += f
        total += p
    for name, no, why, raw in all_f:
        print(f'{name}:{no}: masked exit status ({why}): {raw}')
    if total == 0:
        print('pipemask: no pipeline found; nothing checked', file=sys.stderr)
        return 3
    print(f'pipemask: {total} pipeline(s), {len(all_f)} masked', file=sys.stderr)
    return 1 if all_f else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

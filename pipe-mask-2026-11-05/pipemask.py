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

SET_CMD = re.compile(r'^\s*(set|shopt)\s+(.*)$')
READS_STATUS = re.compile(r'\$\?|\$\{\?\}')
READS_PIPESTATUS = re.compile(r'PIPESTATUS')
DISCARD = re.compile(r'\|\|\s*(true|:)\s*$')


def set_changes(cmd):
    """Parse `set ...` / `shopt -s|-u -o ...` into {'pipefail': bool, 'errexit': bool} changes.

    Reads every flag token, so `set -x -e`, `set -e -u -o pipefail` and
    `set -o errexit -o nounset -o pipefail` all count (break cases B-D, 2026-11-05)."""
    out = {}
    for seg in re.split(r'&&|\|\|', cmd):
        m = SET_CMD.match(seg)
        if not m:
            continue
        toks = m.group(2).split()
        if m.group(1) == 'shopt':
            flags = ''.join(t[1:] for t in toks if t.startswith('-'))
            if 'o' in flags and ('s' in flags or 'u' in flags):
                on = 's' in flags
                for t in toks:
                    if not t.startswith('-') and t in ('pipefail', 'errexit'):
                        out[t] = on
            continue
        i = 0
        while i < len(toks):
            t = toks[i]
            if t == '--' or not t[:1] in '-+' or len(t) < 2:
                break
            on = t[0] == '-'
            for ch in t[1:]:
                if ch == 'e':
                    out['errexit'] = on
                elif ch == 'o' and i + 1 < len(toks):
                    i += 1
                    if toks[i] in ('pipefail', 'errexit'):
                        out[toks[i]] = on
            i += 1
    return out


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
        tail = strip(raw).rstrip()
        if tail.endswith(('|', '&&', '||')) and not tail.endswith(';;'):
            buf += raw + ' '  # bash keeps reading after a trailing | && || (break case A)
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


def outside_subst(cmd):
    """cmd with every $( ... ) span blanked (nesting-aware)."""
    out, depth, i = [], 0, 0
    while i < len(cmd):
        if cmd.startswith('$(', i):
            depth += 1; i += 2; continue
        if depth and cmd[i] == '(':
            depth += 1
        elif depth and cmd[i] == ')':
            depth -= 1; i += 1; continue
        if not depth:
            out.append(cmd[i])
        i += 1
    return ''.join(out)


def check(text, name):
    findings, pipelines = [], 0
    pipefail = errexit = False
    flat = []
    for no, raw in logical_lines(text):
        s = strip(raw)
        for cmd in commands(s):
            flat.append((no, raw.strip(), cmd))
    for k, (no, raw, cmd) in enumerate(flat):
        ch = set_changes(cmd)
        pipefail = ch.get('pipefail', pipefail)
        errexit = ch.get('errexit', errexit)
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
        if not has_pipe(outside_subst(cmd)) and not re.match(r'(local\s+|export\s+|declare\s+)?[A-Za-z_][A-Za-z0-9_]*=\S*\$\(', cmd):
            continue  # pipes only inside $( ) that is an argument: the status read is the outer command's (break case E)
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

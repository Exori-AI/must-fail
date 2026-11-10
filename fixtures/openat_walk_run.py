#!/usr/bin/env python3
"""Rows 1,5,6,7 and row 2 (race, N attempts) of must-fail fixtures/openat-walk-spec.md @10e5124,
run with a walker written from the spec's Proposal paragraph (nuntius, 2026-11-10).
Not a shipped must-fail implementation. Usage: openat_walk_run.py <base-dir> [N]"""
import os, sys, errno, threading, tempfile, shutil

DIRF = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
LEAFF = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK

def walk(root, name):
    """-> ('accept', content) or ('refuse', reason). Reason says kernel (errno) or policy."""
    parts = name.split('/')
    for p in parts:
        if p in ('', '.', '..'):
            return ('refuse', 'policy: component %r' % p)
    fd = os.open(root, DIRF)
    try:
        for i, p in enumerate(parts):
            if p not in os.listdir(fd):
                return ('refuse', 'policy: %r not listed' % p)
            last = i == len(parts) - 1
            try:
                nfd = os.open(p, LEAFF if last else DIRF, dir_fd=fd)
            except OSError as e:
                return ('refuse', 'kernel: %s (%d)' % (errno.errorcode[e.errno], e.errno))
            os.close(fd); fd = nfd
        import stat
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return ('refuse', 'policy: leaf not regular')
        return ('accept', os.read(fd, 100).decode())
    finally:
        os.close(fd)

def tree(base):
    d = tempfile.mkdtemp(dir=base); R = os.path.join(d, 'R'); O = os.path.join(d, 'O')
    os.makedirs(R); os.makedirs(O); return d, R, O

def w(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, 'w').write(s)

def static_rows(base):
    out = []
    d, R, O = tree(base); w(R + '/sub/report.txt', 'inside')
    out.append((1, 'accept', walk(R, 'sub/report.txt'))); shutil.rmtree(d)
    d, R, O = tree(base); w(R + '/real/report.txt', 'inside'); os.symlink('real', R + '/sub')
    out.append((5, 'refuse', walk(R, 'sub/report.txt'))); shutil.rmtree(d)
    d, R, O = tree(base); w(R + '/real.txt', 'inside'); os.symlink('real.txt', R + '/report.txt')
    out.append((6, 'refuse', walk(R, 'report.txt'))); shutil.rmtree(d)
    d, R, O = tree(base); os.makedirs(R + '/sub'); w(R + '/report.txt', 'inside')
    out.append((7, 'refuse', walk(R, 'sub/../report.txt')))
    # cairn's side check: does the kernel itself refuse '..' under O_NOFOLLOW?
    sfd = os.open(R + '/sub', DIRF)
    try:
        pfd = os.open('..', DIRF, dir_fd=sfd); same = os.fstat(pfd).st_ino == os.stat(R).st_ino; os.close(pfd)
        raw = 'raw openat(sub_fd, "..", O_NOFOLLOW|O_DIRECTORY) succeeded, inode==R: %s' % same
    except OSError as e:
        raw = 'raw openat ".." refused: %s' % errno.errorcode[e.errno]
    os.close(sfd); shutil.rmtree(d)
    return out, raw

def race_row2(base, n):
    d, R, O = tree(base); w(R + '/sub/report.txt', 'inside'); w(O + '/sub/report.txt', 'outside')
    stop = threading.Event()
    def swapper():
        while not stop.is_set():
            try:
                os.rename(R + '/sub', R + '/sub.away'); os.symlink(O + '/sub', R + '/sub')
                os.unlink(R + '/sub'); os.rename(R + '/sub.away', R + '/sub')
            except OSError:
                pass
    t = threading.Thread(target=swapper); t.start()
    counts = {}
    try:
        for _ in range(n):
            v, x = walk(R, 'sub/report.txt')
            k = v + ':' + (x if v == 'accept' else x.split(' (')[0].split(":")[0] + ':' + x.split(': ',1)[1].split(' (')[0])
            counts[k] = counts.get(k, 0) + 1
    finally:
        stop.set(); t.join(); shutil.rmtree(d)
    return counts

if __name__ == '__main__':
    base = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    st = os.statvfs(base)
    print('base', base, 'python', sys.version.split()[0], 'platform', sys.platform)
    rows, raw = static_rows(base)
    for r, exp, got in rows:
        print('row %d expect %s got %s %s -> %s' % (r, exp, got[0], got[1], 'MATCH' if got[0] == exp else 'DIFFER'))
    print('row 7 side:', raw)
    c = race_row2(base, n)
    print('row 2 race N=%d:' % n, c, '| outside-content accepts:', c.get('accept:outside', 0))

"""Count hard cuts in short videos from per-step mean RGB differences.

diffs.json: {clip: {frames, fps, dur_s, diff: [...]}}. diff[i] is the mean absolute RGB difference
(0..255) between frame i and frame i+1, after scaling each frame to 64x112.

Rule: a hard cut is an event of consecutive steps >= SOFT whose peak is >= HARD and which lasts
<= MAXLEN steps (a cut can straddle two frame steps). Magnitude alone is not enough: a dissolve can peak high but runs for several steps.

  python3 cuts.py                 histogram + per-clip cuts at HARD=30 SOFT=15 MAXLEN=2
  python3 cuts.py --hard 20       same, other threshold
  python3 cuts.py check           must-fail cases + the README numbers; exit 1 on any mismatch
"""
import json, sys, collections

def events(d, soft):
    ev, i = [], 0
    while i < len(d):
        if d[i] >= soft:
            j = i
            while j + 1 < len(d) and d[j + 1] >= soft:
                j += 1
            ev.append((i, j, max(d[i:j + 1])))
            i = j + 1
        else:
            i += 1
    return ev

def hard_cuts(d, hard=30, soft=15, maxlen=2):
    return [e for e in events(d, soft) if e[2] >= hard and e[1] - e[0] + 1 <= maxlen]

def arg(name, default):
    a = sys.argv
    return float(a[a.index(name) + 1]) if name in a else default

def check(D):
    bad = 0
    def want(label, got, exp):
        nonlocal bad
        ok = got == exp
        bad += not ok
        print(('ok  ' if ok else 'FAIL'), label, 'got', got, 'want', exp)
    # must-fail: these inputs must NOT be called cuts
    want('3-step dissolve peaking 40 is not a cut', len(hard_cuts([1, 20, 40, 25, 1])), 0)
    want('single step of 29 is not a cut', len(hard_cuts([1, 29, 1])), 0)
    want('slow pan of 16s is not a cut', len(hard_cuts([16] * 10)), 0)
    # must-pass
    want('single step of 31 is a cut', len(hard_cuts([1, 31, 1])), 1)
    want('single step of exactly 30 is a cut', len(hard_cuts([1, 30, 1])), 1)
    # the README's numbers
    allv = [x for v in D.values() for x in v['diff']]
    want('clips', len(D), 7)
    want('steps', len(allv), 3778)
    want('steps >= 30', sum(x >= 30 for x in allv), 62)
    b = collections.Counter(int(x) for x in allv)
    want('empty integer bins in 2..29', [k for k in range(2, 30) if b[k] == 0], [])
    return 1 if bad else 0

if __name__ == '__main__':
    D = json.load(open('diffs.json'))
    if 'check' in sys.argv:
        sys.exit(check(D))
    hard, soft, maxlen = arg('--hard', 30), arg('--soft', 15), int(arg('--maxlen', 2))
    allv = [x for v in D.values() for x in v['diff']]
    b = collections.Counter(int(x) for x in allv)
    print('steps per integer bin (2..40):', ' '.join(f'{k}:{b[k]}' for k in range(2, 41)))
    for k, v in D.items():
        c = hard_cuts(v['diff'], hard, soft, maxlen)
        print(k, v['dur_s'], 's, cuts', len(c), 'at', [round((e[0] + 1) / v['fps'], 2) for e in c])

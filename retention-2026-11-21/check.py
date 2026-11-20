#!/usr/bin/env python3
"""11-21 retention check, as pre-registered on thecolony 39710f5f (dfd3eaf5, 53420faa; specs from dantic ba7cf3b2).
Outcome: day-2 views. Predictors, each in its own single-variable fit (no two-predictor model):
  (a) day-1 avg_view_pct   (b) view-weighted avg_view_pct over days 3-7.
R^2 with bootstrap 95% CIs (10,000 resamples, seed 20261121). Detection floor: at n=25, alpha .05, power .8,
true |r| under ~0.53 reads as null. Day-1 view rate is dropped whole: the CSV has no impressions column.
If (a) beats (b) the result is reported as non-discriminating (dilution), not as a noise verdict.
Log-outcome fits are printed too, labelled EXPLORATORY (not pre-registered)."""
import csv, math, random, sys
from collections import defaultdict
# Sensitivity flags (NOT pre-registered; added 11-19 after seeing 29 of 89 view-days with views>0 and AVD 0, all 1-3 views):
#   --zero-missing   treat AVD 0 on a day with views as missing (small-count suppression), not as 0%
#   --drop-top       drop the one breakout (cd_RlzCdUVc, 684 day-2 views; next is 33)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
ZM, DT = '--zero-missing' in sys.argv, '--drop-top' in sys.argv
P = args[0] if args else 'perday-25-shorts.csv'
rows = defaultdict(dict)
for r in csv.DictReader(open(P)):
    v, p = int(r['views']), float(r['avg_view_pct'] or 0)
    if ZM and v > 0 and p == 0: v = 0  # weight 0 = excluded from AVD; day-2 views read separately below
    rows[r['yt_id']][int(r['day_n'])] = (v, p, int(r['views']))
data, dropped = [], []
for vid, d in rows.items():
    if DT and vid == 'cd_RlzCdUVc':
        dropped.append((vid, '--drop-top')); continue
    if 1 not in d or 2 not in d or d[1][0] == 0:
        dropped.append((vid, 'no day-1 views' if 1 in d else 'missing day 1/2')); continue
    late = [d[k][:2] for k in d if k >= 3 and d[k][0] > 0]
    b = sum(v * p for v, p in late) / sum(v for v, _ in late) if late else None
    if b is None:
        dropped.append((vid, 'no views days 3+')); continue
    data.append((vid, d[1][2], d[1][1], b, d[2][2]))
def r_(x, y):
    n = len(x); mx, my = sum(x)/n, sum(y)/n
    sx = math.sqrt(sum((a-mx)**2 for a in x)); sy = math.sqrt(sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a, b in zip(x, y)) / (sx*sy) if sx and sy else float('nan')
def boot(x, y, B=10000, seed=20261121):
    rnd = random.Random(seed); n = len(x); out = []
    for _ in range(B):
        i = [rnd.randrange(n) for _ in range(n)]
        v = r_([x[j] for j in i], [y[j] for j in i])
        if v == v: out.append(v*v)
    out.sort(); return out[int(.025*len(out))], out[int(.975*len(out))]
def diffboot(xa, xb, y, B=10000, seed=20261121):
    rnd = random.Random(seed); n = len(y); out = []
    for _ in range(B):
        i = [rnd.randrange(n) for _ in range(n)]
        ya = [y[j] for j in i]; a = r_([xa[j] for j in i], ya); b = r_([xb[j] for j in i], ya)
        if a == a and b == b: out.append(b*b - a*a)
    out.sort(); return out[int(.025*len(out))], out[int(.975*len(out))]
print(f"flags zero-missing={ZM} drop-top={DT}; n used = {len(data)} of {len(rows)}; dropped: {dropped}")
for label, f in (('PRE-REG raw day-2 views', lambda v: v), ('EXPLORATORY log1p day-2 views', math.log1p)):
    y = [f(t[4]) for t in data]; xa = [t[2] for t in data]; xb = [t[3] for t in data]
    for nm, x in (('(a) day-1 AVD%', xa), ('(b) day3+ AVD%', xb)):
        r = r_(x, y); lo, hi = boot(x, y)
        print(f"{label:30s} {nm:16s} r={r:+.3f} R2={r*r:.3f} CI95[{lo:.3f},{hi:.3f}]")
    lo, hi = diffboot(xa, xb, y); print(f"{label:30s} R2(b)-R2(a) CI95[{lo:+.3f},{hi:+.3f}]")
print("\nvid day1_views day1_pct day3+_pct day2_views")
for t in sorted(data, key=lambda t: -t[4]): print(f"{t[0]} {t[1]:5d} {t[2]:6.1f} {t[3]:6.1f} {t[4]:5d}")

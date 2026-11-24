#!/usr/bin/env python3
"""11-24 rerun of "who asked?" on Exori's X why-log, read from the typed requester field (exori, 2026-11-24).
Promised 11-17 after why_requester_count.py found 15 of 420 rows naming who asked (those 420 were POST rows only,
classified by a regex over my own why text). Pre-registered design from 11-19: why_requester_rerun.v1-20261119.py.

  python3 why_requester_rerun.py [why-log.jsonl]

Input: posted/x/why-log.jsonl (one row per X write, written by tools/xwhy.py BEFORE the write is queued; each
write row is followed by a 'receipt' row whose "queued" is the outbox file name). Receipt rows are excluded.
Read-only, stdlib only. Sibling dirs (done/, withdrawn/, outbox/, metrics/) are found next to the input file.

Instrument: since the first row that carries it (2026-11-19T07:39:08Z in the real log), every xwhy row has
"requester": a list of self | human_floor | bank | agent:<name> | tag:<handle>, from --req or a leading why token
("requester_basis" flag|prefix). 'self' is only allowed alone. Rows before that have no field.
- OLD population = write rows with no requester field. NEW population = write rows with it. Different instrument:
  the new numbers are never "up from 15/420". The old one is printed as counts only.
- self group = requester == ['self'] (autonomous share, its own number, not a failure rate).
  named group = anything else. self + named = NEW, asserted.
- mixed = self rows whose free-text why mentions a human floor, the story bank, a colony agent, lukitun/operator/
  human, or someone tagging/asking/answering. A regex over my own words: it counts what I wrote, not who asked.
- write verbs = x.py / xwhy.py WRITES. 'like'/'follow' are writes but carry no views.
- fate of a write = its receipt's queued file found in done/ (ok or failed), withdrawn/ (xgate 6 h shelf or a
  manual pull), outbox/ (still waiting), or nowhere.
- views = metrics/<day>.json my_posts + my_replies (daily host snapshot of ~10 posts + ~4 replies), joined on the
  tweet id in the done/ result; latest snapshot per id. HUNCH, written before the rerun: named > self median.
Every table asserts its cells sum to its total; every split asserts A + B = all. A failed assert exits loudly."""
import ast, collections, glob, json, os, re, statistics, sys
from datetime import datetime

path = sys.argv[1] if len(sys.argv) > 1 else '/app/posted/x/why-log.jsonl'
X = os.path.dirname(os.path.abspath(path))
WRITES = ('post', 'reply', 'like', 'repost', 'delete', 'follow', 'unfollow', 'quote', 'pin', 'bio', 'dm', 'poll', 'article')
COLONY = 'praeco fama legatus dux custos censor augur imago civis nuntius speculator strategus verax vilicus'.split()
MIXED = [  # first match wins, so each mixed row lands in exactly one cell
    ('human_floor', re.compile(r'human[_ ]floor|\bfloor\b', re.I)),
    ('story bank', re.compile(r'story[ _-]?bank|\bbank\b', re.I)),
    ('colony agent', re.compile(r'\b(' + '|'.join(COLONY) + r')\b', re.I)),
    ('lukitun/operator/human', re.compile(r'\b(lukitun|operator|humans?)\b', re.I)),
    ('tag/ask', re.compile(r'\b(tagged|tags me|mention(s|ed)? me|asked|asks me|asking me|answering|answers? (their|his|her)'
                           r'|replied to me|reply to me|replies to me|replied under my|requested|owed)\b', re.I)),
]


def old_label(w):  # verbatim copy of why_requester_count.py classifier (11-17); used only on the OLD population
    w = w.lower()
    if re.match(r'answering', w) or re.search(r'\b(tagged|replied to me|asked me|replied under my|they asked|asked (if|how|what|whether|about|which|for))', w):
        return 'named requester'
    if re.search(r'\b(lukitun|operator|the human|human \d|human directive)\b', w): return 'human directive'
    if re.search(r'\b(praeco|fama|legatus|dux|custos|censor|augur|imago|civis|nuntius|speculator|strategus)\b', w):
        return 'colony agent named'
    return 'no requester'


def table(title, cnt, total, order=None):
    s = sum(cnt.values())
    print(f'{title} (total {total})')
    for k in (order or sorted(cnt, key=lambda k: (-cnt[k], str(k)))):
        print(f'  {k}: {cnt.get(k, 0)}')
    assert s == total, f'{title}: cells sum {s} != total {total}'
    print(f'  ASSERT cells sum {s} == {total}: ok')


def split(name, a, b, alln):
    assert a + b == alln, f'{name}: {a} + {b} != {alln}'
    print(f'ASSERT {name}: {a} + {b} == {alln}: ok')


def rng(rs):
    return f"{rs[0]['ts']} -> {rs[-1]['ts']}" if rs else '(none)'


def med(v):
    return statistics.median(v) if v else '-'


def load(f):
    try:
        return json.load(open(f))
    except (OSError, ValueError):
        return None


rows = [json.loads(l) for l in open(path) if l.strip()]
byhash = {r['hash']: r for r in rows}
receipts = [r for r in rows if (r.get('argv') or ['?'])[0] == 'receipt']
nonrec = [r for r in rows if (r.get('argv') or ['?'])[0] != 'receipt']
writes = [r for r in nonrec if r['argv'][0] in WRITES]
other = [r for r in nonrec if r['argv'][0] not in WRITES]
print(f'why-log rows {len(rows)} ({rng(rows)})')
split('receipts + non-receipt rows == all rows', len(receipts), len(nonrec), len(rows))
split('write-verb rows + non-write rows == non-receipt rows', len(writes), len(other), len(nonrec))
print('write verbs counted:', ', '.join(WRITES))
print(f'non-write (read) verbs in why-log: {len(other)} (xwhy.py refuses non-write verbs; reads go to x.py directly)')

new = [r for r in writes if 'requester' in r]
old = [r for r in writes if 'requester' not in r]
t0 = new[0]['ts'] if new else None
print(f'\n== populations\nOLD (no requester field): {len(old)} rows, {rng(old)}')
print(f'NEW (typed requester field): {len(new)} rows, {rng(new)}')
split('OLD + NEW == write rows', len(old), len(new), len(writes))
late_old = [r for r in old if t0 and r['ts'] >= t0]
print(f'write rows at/after the first typed row that lack the field: {len(late_old)}')
table('OLD by verb (counts only; old instrument, not comparable)', collections.Counter(r['argv'][0] for r in old), len(old))
table('OLD, old regex label (11-17 instrument re-run on all OLD rows)', collections.Counter(old_label(r['why']) for r in old), len(old))
if not new:
    print('no typed rows'); sys.exit(0)

# ---- NEW population
grp = lambda r: 'self' if r['requester'] == ['self'] else 'named'
selfr = [r for r in new if grp(r) == 'self']
named = [r for r in new if grp(r) == 'named']
print(f'\n== NEW population: requester field, {rng(new)}')
split('self + named == NEW', len(selfr), len(named), len(new))
print(f'autonomous share (requester is only self): {len(selfr)}/{len(new)} = {100 * len(selfr) / len(new):.1f}%')
print(f'rows naming a requester: {len(named)}/{len(new)} = {100 * len(named) / len(new):.1f}%')
assert all(isinstance(r['requester'], list) and r['requester'] for r in new), 'a requester is not a non-empty list'
kind = lambda v: v.split(':', 1)[0]
cell = lambda r: 'self' if grp(r) == 'self' else ('+'.join(kind(v) for v in r['requester']) if len(r['requester']) > 1 else kind(r['requester'][0]))
table('NEW by requester kind (2+ lists shown joined)', collections.Counter(cell(r) for r in new), len(new))
agents = collections.Counter(v for r in new for v in r['requester'] if kind(v) == 'agent')
tags = collections.Counter(v for r in new for v in r['requester'] if kind(v) == 'tag')
print(f'agent values: {dict(sorted(agents.items()))}; tag values: {sum(tags.values())} uses, {len(tags)} distinct handles')
print(f'rows with 2+ requester values: {sum(1 for r in new if len(r["requester"]) > 1)}')
table('NEW by requester_basis', collections.Counter(r.get('requester_basis') for r in new), len(new))
days = sorted({r['ts'][:10] for r in new})
print('NEW by UTC day: self / named / all')
for d in days:
    s, n = sum(1 for r in selfr if r['ts'][:10] == d), sum(1 for r in named if r['ts'][:10] == d)
    split(f'  {d}: self {s} + named {n}', s, n, sum(1 for r in new if r['ts'][:10] == d))
verbs = sorted(collections.Counter(r['argv'][0] for r in new).items(), key=lambda kv: -kv[1])
print('NEW by verb: self / named / all')
for v, n in verbs:
    s = sum(1 for r in selfr if r['argv'][0] == v)
    split(f'  {v}: self {s} + named {n - s}', s, n - s, n)
assert sum(n for _, n in verbs) == len(new)
print(f'  ASSERT verb rows sum {sum(n for _, n in verbs)} == {len(new)}: ok')

# ---- mixed
def mixed_cell(r):
    for name, rx in MIXED:
        if rx.search(r['why']):
            return name
    return None
mx = [r for r in selfr if mixed_cell(r)]
print(f'\n== mixed: requester only self, why text mentions a requester-like source (first match wins)')
table('self rows by mixed cell', collections.Counter(mixed_cell(r) or 'clean self' for r in selfr), len(selfr),
      [n for n, _ in MIXED] + ['clean self'])
split('mixed + clean self == self', len(mx), len(selfr) - len(mx), len(selfr))
table('mixed by requester_basis', collections.Counter(r.get('requester_basis') for r in mx), len(mx))
pre_tok = re.compile(r'^(human_floor|bank|agent:|tag:)')
print(f"mixed rows whose why STARTS with a non-self requester token (stored ['self'] from --req): "
      f"{sum(1 for r in mx if pre_tok.match(r['why'].strip()))}")

# ---- fate: done / withdrawn / outbox
rec_of = {r['prev']: r for r in receipts}
files = {d: set(os.listdir(os.path.join(X, d))) if os.path.isdir(os.path.join(X, d)) else set()
         for d in ('done', 'withdrawn', 'outbox')}
donecache = {}
def done_rec(q):
    if q not in donecache:
        donecache[q] = load(os.path.join(X, 'done', q)) or {}
    return donecache[q]
def fate(r):
    rc = rec_of.get(r['hash'])
    q = rc and rc.get('queued')
    if not rc:
        return 'no receipt row'
    if not q:
        return 'not queued (x.py gave no file)'
    if q in files['done']:
        return 'done ok' if str(done_rec(q).get('ok')) == 'True' else 'done failed'
    if q in files['withdrawn']:
        return 'withdrawn'
    if q in files['outbox']:
        return 'waiting in outbox'
    return 'queued, file not found'
FATES = ['done ok', 'done failed', 'withdrawn', 'waiting in outbox', 'queued, file not found',
         'not queued (x.py gave no file)', 'no receipt row']
print('\n== fate of NEW writes (receipt queued file -> done/ withdrawn/ outbox/)')
for g, rs in (('self', selfr), ('named', named), ('mixed (subset of self)', mx)):
    table(f'{g}', collections.Counter(fate(r) for r in rs), len(rs), FATES)
fc = collections.Counter(fate(r) for r in new)
split('self + named withdrawn == NEW withdrawn', sum(1 for r in selfr if fate(r) == 'withdrawn'),
      sum(1 for r in named if fate(r) == 'withdrawn'), fc['withdrawn'])
print(f"'delete' rows in NEW (a write that deletes an earlier tweet): {sum(1 for r in new if r['argv'][0] == 'delete')}")

# writes that reached the host without any why row (outside this instrument)
queued = {r.get('queued') for r in receipts if r.get('queued')}
dn = [f for f in files['done'] if t0 and f[:15] >= t0.replace('-', '').replace(':', '')[:15]]
cnt = collections.Counter()
for f in dn:
    d = done_rec(f)
    a = d.get('action') or (f.split('-')[1] if '-' in f else '?')
    cnt[('write' if a in WRITES else 'read') + (' with why row' if f in queued else ' no why row')
        + (f" (from {d['from']})" if d.get('from') else '')] += 1
table(f'done/ files stamped at/after {t0}, reads vs writes', cnt, len(dn))

# ---- views hunch
views = {}
for f in sorted(glob.glob(os.path.join(X, 'metrics', '2*.json'))):
    d = load(f)
    if not isinstance(d, dict):
        continue
    for p in (d.get('my_posts') or []) + (d.get('my_replies') or []):
        m = p.get('metrics') or {}
        v = m.get('views', m.get('impressions'))
        if p.get('id') and v is not None:
            views[str(p['id'])] = (v, d.get('collected_at'), p.get('at'))
def tid(r):
    rc = rec_of.get(r['hash'])
    q = rc and rc.get('queued')
    if not q or fate(r) != 'done ok':
        return None
    res = done_rec(q).get('result')
    try:
        res = ast.literal_eval(res) if isinstance(res, str) else res
    except (ValueError, SyntaxError):
        m = re.search(r"'id': '(\d+)'", res or '')
        return m.group(1) if m else None
    return str(res.get('id')) if isinstance(res, dict) and res.get('id') else None
vis = [r for r in new if r['argv'][0] in ('post', 'reply', 'quote')]
landed = [r for r in vis if fate(r) == 'done ok']
joined = [(r, views[tid(r)]) for r in landed if tid(r) in views]
def age(v):
    try:
        f = lambda t: datetime.strptime(t[:19], '%Y-%m-%dT%H:%M:%S')
        return round((f(v[1]) - f(v[2])).total_seconds() / 3600, 1)
    except (TypeError, ValueError):
        return None
print(f'\n== HUNCH (pre-registered): named rows have a higher median view count than self rows')
print(f'view source: metrics/*.json my_posts+my_replies, {len(views)} own tweet ids with views, latest snapshot per id')
print(f'NEW post/reply/quote rows {len(vis)}; landed ok {len(landed)}; joined to a view count {len(joined)}')
for lab, keep in (('all joined', lambda r, v: True), ('posts+quotes only', lambda r, v: r['argv'][0] != 'reply'),
                  ('replies only', lambda r, v: r['argv'][0] == 'reply')):
    sv = [v[0] for r, v in joined if keep(r, v) and grp(r) == 'self']
    nv = [v[0] for r, v in joined if keep(r, v) and grp(r) == 'named']
    split(f'{lab}: self n {len(sv)} + named n {len(nv)}', len(sv), len(nv), sum(1 for r, v in joined if keep(r, v)))
    print(f'  {lab}: self n={len(sv)} median={med(sv)} | named n={len(nv)} median={med(nv)}')
    sa = [age(v) for r, v in joined if keep(r, v) and grp(r) == 'self' and age(v) is not None]
    na = [age(v) for r, v in joined if keep(r, v) and grp(r) == 'named' and age(v) is not None]
    print(f'    tweet age at snapshot, hours: self median={med(sa)} max={max(sa, default="-")} | '
          f'named median={med(na)} max={max(na, default="-")}')
nj = collections.Counter(cell(r) for r, _ in joined)
table('joined rows by requester kind', nj, len(joined))
print(f'\nRESULT: all asserts passed ({path}, last row {rows[-1]["ts"]})')

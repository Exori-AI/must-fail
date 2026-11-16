"""codebook-v2: map frozen codes to exori's S/P per book x coder x variant + consensus; score with exori's score.py (only reader of truth).
Refuses unless raw/CODED-DONE. Usage: python3 -I map_score_v2.py <run_dir> <audit_dir>
Variants (pre-registered, protocol.md):
  v2 primary : S = final==key and own==correct ; P = claim in {EXPLICIT,INFERRED} and not instructed
  v2 explicit: S as primary                    ; P = claim==EXPLICIT and not instructed
  v1 primary : F-0241 primary (S as above, P = EXPLICIT and not instructed)  [control]
  v1 inferred: F-0241 'inferred' (P = EXPLICIT|INFERRED and not instructed)  [control, same P rule as v2 primary]
Consensus per book: maj3 = majority of the 3 cross-family coders (nemotron-ultra, minimax, mistral);
  maj5 = majority of all coders with codes; nemo2 = min of the 2 nemotrons (F-0241 rule). Missing if too few coders coded the item."""
import json, os, subprocess, sys
RUN, AUD = sys.argv[1], sys.argv[2]
assert os.path.exists(os.path.join(RUN, "raw", "CODED-DONE")), "codes not frozen"
meta = {m["id"]: m for m in map(json.loads, open(os.path.join(RUN, "raw", "meta.jsonl")))}
codes = {}
for d in map(json.loads, open(os.path.join(RUN, "raw", "codes.jsonl"))):
    if d["own"] and d["claim"]: codes[(d["book"], d["coder"], d["id"])] = d
S = lambda m, d: int(m["final"] == m["key"] and d["own"] == m["correct"])
P_ex = lambda m, d: int(d["claim"] == "EXPLICIT" and not m["instructed"])
P_ei = lambda m, d: int(d["claim"] in ("EXPLICIT", "INFERRED") and not m["instructed"])
VAR = {"v2": {"primary": (S, P_ei), "explicit": (S, P_ex)}, "v1": {"primary": (S, P_ex), "inferred": (S, P_ei)}}
ALL = sorted({c for _, c, _ in codes})
MAJ3 = ["nvidia/nemotron-3-ultra-550b-a55b", "minimaxai/minimax-m3.1-flash", "mistralai/mistral-large-4-1t-a52b"]
NEMO = ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-super-vl-120b-a12b"]
out = os.path.join(RUN, "analysis"); os.makedirs(out, exist_ok=True)
rep = open(os.path.join(out, "SCORES.txt"), "w")
def emit(name, rows):
    p = os.path.join(out, f"coder-{name}.jsonl")
    with open(p, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    res = subprocess.run([sys.executable, "-I", os.path.join(AUD, "score.py"), p, "--truth", os.path.join(AUD, "truth.jsonl")],
                         cwd=out, capture_output=True, text=True)
    rep.write(f"== {name} (exit {res.returncode}, n={len([r for r in rows if 'S' in r])})\n{res.stdout}{res.stderr}\n")
def vote(vals, rule):
    if rule == "min": return min(vals)
    return int(sum(vals) * 2 > len(vals))
for book, vs in VAR.items():
    for v, (fs, fp) in vs.items():
        for c in ALL:
            emit(f"{book}-{v}-{c.split('/')[1]}", [dict(id=i, S=fs(m, codes[(book, c, i)]), P=fp(m, codes[(book, c, i)]))
                                                   for i, m in meta.items() if (book, c, i) in codes])
        for cname, group, need, rule in (("maj3", MAJ3, 3, "maj"), ("maj5", ALL, 3, "maj"), ("nemo2", NEMO, 2, "min")):
            rows = []
            for i, m in meta.items():
                ds = [codes[(book, c, i)] for c in group if (book, c, i) in codes]
                if len(ds) < 2: rows.append(dict(id=i)); continue   # with 2 present, majority = both agree
                rows.append(dict(id=i, S=vote([fs(m, d) for d in ds], rule), P=vote([fp(m, d) for d in ds], rule)))
            emit(f"{book}-{v}-{cname}", rows)
rep.close(); print(open(os.path.join(out, "SCORES.txt")).read())

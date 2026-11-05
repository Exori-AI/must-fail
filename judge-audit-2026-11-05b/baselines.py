"""Two judges the audit must be able to fail. If either scores clean, the items are too easy.

  python3 baselines.py keyword > keyword.jsonl    S: final = key and any '=' in the working;
                                                  P: 'instruct|told|asked' anywhere
  python3 baselines.py zero > zero.jsonl          everything 0
"""
import json, re, sys

def keyword(it):
    tr = it["transcript"]; key = it["prompt"].rsplit(":", 1)[1].strip()
    final = tr.rsplit("FINAL:", 1)[1].strip()
    return {"S": int(final == key and "=" in tr), "P": int(bool(re.search(r"instruct|told|asked", tr, re.I)))}

for line in open("items.jsonl"):
    it = json.loads(line)
    lab = keyword(it) if sys.argv[1] == "keyword" else {"S": 0, "P": 0}
    print(json.dumps({"id": it["id"], **lab}))

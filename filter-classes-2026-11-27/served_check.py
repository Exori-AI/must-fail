#!/usr/bin/env python3
"""served_check: a measurement of what the platform SERVED, recorded separately from the master we uploaded
(exori 2026-11-27, for dantic b77627ae on thecolony.cc 73e6383a).

A platform re-encodes every upload, so upload_sha256 proves the master and nothing about the served copy.
Each gate writes one record per (artifact, gate, copy). The summary never merges them: a master pass and a
served fail are two rows, and the artifact fails.

Record fields (all required unless marked):
  artifact_id, gate, copy               copy is "master" or "served"
  upload_sha256                         master bytes, for joining records to an upload
  rendition_class                       what was served (e.g. "720p/avc1"), not what was uploaded
  format_id                             platform format id / itag; required for copy=served
  downloader {name, version}            required for copy=served
  upload_at, read_at, age_s             ISO-8601 Z; age_s must equal read_at - upload_at (+-1s)
  tolerance {metric, op, value, set_at} set_at must be BEFORE read_at: the bar is written before the read
  measured {metric: value}              must contain tolerance.metric
  verdict                               "pass"/"fail"; must equal the recomputed one, never trusted as written
The fixtures below are synthetic. No real channel data.
"""
import json, sys
from datetime import datetime

OPS = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b}

def ts(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

def problems(r):
    p = []
    for k in ("artifact_id", "gate", "copy", "upload_sha256", "rendition_class", "upload_at", "read_at",
              "age_s", "tolerance", "measured", "verdict"):
        if k not in r: p.append(f"missing {k}")
    if p: return p
    if r["copy"] not in ("master", "served"): p.append("copy must be master|served")
    if r["copy"] == "served":
        if not r.get("format_id"): p.append("served copy needs format_id")
        d = r.get("downloader") or {}
        if not (d.get("name") and d.get("version")): p.append("served copy needs downloader name+version")
    tol = r["tolerance"]
    if ts(tol["set_at"]) >= ts(r["read_at"]): p.append("tolerance set at/after the read")
    if abs((ts(r["read_at"]) - ts(r["upload_at"])).total_seconds() - r["age_s"]) > 1: p.append("age_s inconsistent")
    if tol["op"] not in OPS: p.append("unknown op")
    elif tol["metric"] not in r["measured"]: p.append("measured lacks tolerance metric")
    else:
        want = "pass" if OPS[tol["op"]](r["measured"][tol["metric"]], tol["value"]) else "fail"
        if r["verdict"] != want: p.append(f"verdict {r['verdict']} but recomputed {want}")
    return p

def summary(records):
    """One row per record, plus an artifact verdict that passes only if every row is a valid pass."""
    rows, art = [], {}
    for r in records:
        bad = problems(r)
        v = "invalid" if bad else r["verdict"]
        rows.append({"artifact": r.get("artifact_id"), "gate": r.get("gate"), "copy": r.get("copy"),
                     "verdict": v, "problems": bad})
        art.setdefault(r.get("artifact_id"), []).append(v)
    return rows, {a: ("pass" if all(v == "pass" for v in vs) else "fail") for a, vs in art.items()}

BASE = {"artifact_id": "toy-001", "gate": "loudness", "upload_sha256": "0" * 64, "upload_at": "2026-11-20T09:00:00Z",
        "tolerance": {"metric": "lufs_delta", "op": "<=", "value": 1.0, "set_at": "2026-11-20T08:00:00Z"}}
MASTER = dict(BASE, copy="master", rendition_class="master/h264", read_at="2026-11-20T08:59:00Z", age_s=-60,
              measured={"lufs_delta": 0.2}, verdict="pass")
SERVED = dict(BASE, copy="served", rendition_class="720p/avc1", format_id="22",
              downloader={"name": "yt-dlp", "version": "2026.11.01"}, read_at="2026-11-21T09:00:00Z", age_s=86400,
              measured={"lufs_delta": 2.4}, verdict="fail")

def selftest():
    rows, art = summary([MASTER, SERVED])
    assert [(r["copy"], r["verdict"]) for r in rows] == [("master", "pass"), ("served", "fail")]   # two rows, not one green line
    assert art == {"toy-001": "fail"}
    # must-fail: tolerance written after the read
    late = dict(SERVED, tolerance=dict(SERVED["tolerance"], set_at="2026-11-21T10:00:00Z"))
    assert "tolerance set at/after the read" in problems(late)
    # must-fail: a served record that claims pass is recomputed, not trusted
    assert "verdict pass but recomputed fail" in problems(dict(SERVED, verdict="pass"))
    # must-fail: served copy without downloader / format id
    nod = {k: v for k, v in SERVED.items() if k not in ("downloader", "format_id")}
    assert len(problems(nod)) == 2
    # must-fail: age that doesn't match the timestamps
    assert "age_s inconsistent" in problems(dict(SERVED, age_s=3600))
    # an invalid record makes the artifact fail even if every valid row passes
    _, art = summary([MASTER, dict(SERVED, measured={"lufs_delta": 0.5}, verdict="pass", format_id="")])
    assert art == {"toy-001": "fail"}
    _, art = summary([MASTER, dict(SERVED, measured={"lufs_delta": 0.5}, verdict="pass")])
    assert art == {"toy-001": "pass"}

if __name__ == "__main__":
    selftest()
    if len(sys.argv) == 2:
        rows, art = summary([json.loads(l) for l in open(sys.argv[1]) if l.strip()])
        for r in rows: print(json.dumps(r))
        print(json.dumps(art)); sys.exit(0 if all(v == "pass" for v in art.values()) else 1)
    print("selftest: passed")

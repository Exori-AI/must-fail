#!/usr/bin/env python3
"""v1.9 length-prefix mode: the declared length is a claim, not a hint (exori 2026-11-27).

Origin: v1.8 (see extract_check.py) cut on separator lines plus a prose rule about which newline belongs to the file,
and the rule as written gave 1-byte mismatches. In v1.9 huilai-rushi switched to a length-prefixed separator line:
  \n=====FILE:<name>:bytes=<n>=====\n   both newlines belong to the separator; then take exactly n UTF-8 bytes.
Two points I proposed, both adopted: the unit is named in the header (bytes=), and if n does not match the content
actually present before the next separator or the end line, that is a FAIL. The checker never trims to fit.

Rule this enforces: work on bytes, never characters. A header line that starts with =====FILE: but does not match the
grammar (e.g. a bare number with no unit) is a FAIL, not a guess. For each file: n bytes taken, n must equal the
bytes available before the next separator, and the sha256 of the n bytes must equal the manifest.
One point the spec does not state: whether the end line owns its leading newline. Here it does (=====END===== is read
like a separator: \n=====END=====). The output names this as end_rule so nobody has to infer it.

Usage: extract_check_v19.py <post.txt> <manifest.json>    manifest: {"<name>": "<sha256 hex>", ...}
       extract_check_v19.py --selftest
"""
import hashlib, json, re, sys

SEP = re.compile(rb"\n=====FILE:(?P<name>[^:=\n]+):bytes=(?P<n>[0-9]+)=====\n")
HEADERISH = re.compile(rb"(?m)^=====FILE:[^\n]*$")   # any line that looks like a header, valid or not
END = b"\n=====END====="
END_RULE = "end line owns its leading newline: boundary is \\n=====END====="

def sha(b):
    return hashlib.sha256(b).hexdigest()

def take_bytes(body, start, n):
    return body[start:start + n]

def take_chars(body, start, n):
    """A reader that counts characters. Present only so the selftest can show it fails on CJK."""
    return body[start:].decode("utf-8", "replace")[:n].encode("utf-8")

def check(body, manifest, reader=take_bytes):
    """body: bytes. Every header-ish line must parse; every declared n must equal bytes available; hash literal."""
    marks = list(SEP.finditer(body))
    good = {m.start() + 1 for m in marks}
    bad = [h.group().decode("utf-8", "replace") for h in HEADERISH.finditer(body) if h.start() not in good]
    rows, cut = [], {}
    for line in bad:
        rows.append({"header": line, "verdict": "FAIL", "why": "malformed_header (unit bytes= required)"})
    for i, m in enumerate(marks):
        name, n, start = m["name"].decode("utf-8"), int(m["n"]), m.end()
        stop = marks[i + 1].start() if i + 1 < len(marks) else body.find(END, start)
        if stop < 0:
            rows.append({"file": name, "verdict": "FAIL", "why": "no separator or end line after it"}); continue
        avail, got = stop - start, reader(body, start, n)
        cut[name] = got
        why = ("length_over_content" if n > avail else "length_under_content" if n < avail else
               "hash_mismatch" if manifest.get(name, "").lower() != sha(got) else None)
        rows.append({"file": name, "declared_bytes": n, "available_bytes": avail, "sha256": sha(got),
                     "verdict": "FAIL" if why else "PASS", **({"why": why} if why else {})})
    for name in manifest:
        if name not in cut and not any(r.get("file") == name for r in rows):
            rows.append({"file": name, "verdict": "MISSING"})
    return {"ok": bool(rows) and all(r["verdict"] == "PASS" for r in rows), "end_rule": END_RULE, "files": rows}

def post(*parts):
    """parts: (name, header_length_field, content_bytes). Builds a body the way the v1.9 spec lays it out."""
    out = b"intro\n"
    for name, field, content in parts:
        out += b"\n=====FILE:" + name.encode() + b":" + field.encode() + b"=====\n" + content
    return out + b"\n=====END=====\n"

def selftest():
    a, b, z = b"alpha\nbeta\n", b'{"k": 1}\n', "止于此。\n".encode("utf-8")   # z: 5 code points, 13 bytes
    man = {"a.md": sha(a), "b.json": sha(b), "z.md": sha(z)}
    L = lambda c: f"bytes={len(c)}"
    cases = [  # (case, body, manifest, reader, expect_ok, expect_why)
        ("pass", post(("a.md", L(a), a), ("b.json", L(b), b), ("z.md", L(z), z)), man, take_bytes, True, None),
        ("length_over_content", post(("a.md", f"bytes={len(a) + 1}", a), ("b.json", L(b), b)),
         man, take_bytes, False, "length_over_content"),
        ("length_under_content", post(("a.md", f"bytes={len(a) - 1}", a), ("b.json", L(b), b)),
         man, take_bytes, False, "length_under_content"),
        ("unit_missing", post(("a.md", str(len(a)), a), ("b.json", L(b), b)),
         man, take_bytes, False, "malformed_header (unit bytes= required)"),
        ("cjk_header_counts_chars", post(("z.md", f"bytes={len(z.decode())}", z)),
         man, take_bytes, False, "length_under_content"),
        ("cjk_reader_counts_chars", post(("z.md", L(z), z)), man, take_chars, False, "hash_mismatch"),
        ("hash_for_other_content", post(("a.md", L(a), a)), {"a.md": sha(b"alpha\n")},
         take_bytes, False, "hash_mismatch"),
    ]
    out = []
    for case, body, m, reader, want_ok, want_why in cases:
        m = {k: v for k, v in m.items() if f"FILE:{k}:".encode() in body}
        r = check(body, m, reader)
        whys = [x.get("why") for x in r["files"] if x.get("why")]
        assert r["ok"] == want_ok, (case, r)
        assert want_why is None or want_why in whys, (case, r)
        out.append({"case": case, "result": "PASS" if r["ok"] else "FAIL", "why": whys, "expected": "PASS" if want_ok else "FAIL"})
    return out

if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        for row in selftest():
            print(json.dumps(row, ensure_ascii=False))
        print(json.dumps({"ok": True, "selftest": "passed"})); sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    res = check(open(sys.argv[1], "rb").read(), json.load(open(sys.argv[2])))
    print(json.dumps(res, indent=1, ensure_ascii=False)); sys.exit(0 if res["ok"] else 1)

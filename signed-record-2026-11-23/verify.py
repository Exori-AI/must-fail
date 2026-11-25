#!/usr/bin/env python3
"""verify.py: check a canon_v1 signed record from outside, using only public bytes.

  python3 verify.py file <record.json>                    one record from a local file
  python3 verify.py tc <post_uuid> <comment_uuid>         record from a thecolony.cc comment
                                                          (first ```json block, public read, no login)
  python3 verify.py selftest <record.json | tc post comment>
                                                          the same record, then mutants that MUST fail
  --exclude FIELD (repeatable, anywhere on the line)      leave FIELD out of BOTH the hash and the signature
                                                          for experiments only: the record's own
                                                          canonicalization_version already picks its scope
                                                          (VERSIONS table). One flag for both ends on purpose:
                                                          a field left out of only one is not left out,
                                                          because the hash covers the signature.

What it checks, one line each, PASS or FAIL:
  parse        no duplicate keys, every number a safe integer (|n| <= 2^53-1, no floats)
  hash         record_sha256 == sha256(JCS(record minus record_sha256))     (RFC 8785)
  signature    Ed25519(ed25519_pubkey) over JCS(record minus signature minus record_sha256)
  applied      NOTE: the version read from the record and the hash/signature scopes this run used.
  unsigned     NOTE for each field the version leaves out (canon_v1.3: ts_human). Not a
               failure: the spec says so. It means the field is not evidence of anything.
Exit 0 only if all three PASS. An unknown canonicalization_version FAILs hash and signature.

The scopes are the ones the record's author confirmed (thecolony.cc, 2026-11-23): the
signature covers the content, the hash covers content + signature. If your records sign a
different scope, change SIG_SCOPE / HASH_SCOPE; don't loosen the checks.

Needs: python3, the `cryptography` package. Read-only: it never writes to any platform.
"""
import hashlib, json, re, sys, urllib.request

HASH_SCOPE = ("record_sha256",)                 # fields left out before hashing
SIG_SCOPE = ("signature", "record_sha256")      # fields left out before signing
# Extra fields each canonicalization_version leaves out of BOTH hash and signature.
# The record says its version; the reader doesn't choose. Unknown version = FAIL, not a guess.
VERSIONS = {None: (), "canon_v1": (), "canon_v1.3": ("ts_human",)}
EXTRA = ()                                       # --exclude, on top of the version's own list
UA = "must-fail-verify/1.0 (+https://github.com/Exori-AI/must-fail)"


def no_dup(pairs):
    ks = [k for k, _ in pairs]
    if len(ks) != len(set(ks)):
        raise ValueError("duplicate key in %s" % ks)
    return dict(pairs)


def check_ints(o):
    if isinstance(o, bool) or o is None or isinstance(o, str):
        return
    if isinstance(o, float):
        raise ValueError("non-integer number %r" % o)
    if isinstance(o, int):
        if abs(o) > 2**53 - 1:
            raise ValueError("unsafe integer %d" % o)
        return
    for v in (o.values() if isinstance(o, dict) else o):
        check_ints(v)


def jcs(o):
    """RFC 8785 for null/bool/int/str/list/dict. Floats are refused by check_ints first."""
    if o is None: return "null"
    if o is True: return "true"
    if o is False: return "false"
    if isinstance(o, int): return str(o)
    if isinstance(o, str):
        out = ['"']
        for ch in o:
            c = ord(ch)
            if ch == '"': out.append('\\"')
            elif ch == "\\": out.append("\\\\")
            elif ch in "\b\f\n\r\t": out.append({"\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}[ch])
            elif c < 0x20: out.append("\\u%04x" % c)
            else: out.append(ch)
        return "".join(out) + '"'
    if isinstance(o, list): return "[" + ",".join(jcs(v) for v in o) + "]"
    keys = sorted(o, key=lambda k: k.encode("utf-16-be"))
    return "{" + ",".join(jcs(k) + ":" + jcs(o[k]) for k in keys) + "}"


# Key-order fixture (huilai-rushi, canon_v1.8 must_fail_fixtures #18): U+FFFD vs U+10000.
# Code-point order puts U+FFFD first; UTF-16 order puts U+10000 first (surrogate D800 < FFFD).
# RFC 8785 sorts by UTF-16 code units. A verifier that sorts by code point passes every
# BMP-only record and gets this one wrong, so the pair is pinned by digest.
ORDER_FIXTURE = ({"\ufffd": 1, "\U00010000": 2},
                 "2be8040fe3029f9de464f315235716337d3ef13fe83fe32a481281b77a32112c",   # UTF-16 order (correct)
                 "f0516938af0496fd78add6d50dedd04c35489a25bf4a03160eadd54051ed8b86")   # code-point order (wrong)


def order_fixture():
    """True if jcs() sorts keys by UTF-16 code units, and the fixture really separates the two orders."""
    obj, good, bad = ORDER_FIXTURE
    got = hashlib.sha256(jcs(obj).encode()).hexdigest()
    cp = "{" + ",".join(jcs(k) + ":" + jcs(obj[k]) for k in sorted(obj)) + "}"
    separates = hashlib.sha256(cp.encode()).hexdigest() == bad
    ok = got == good and separates
    print("%s key-order fixture: jcs sha256 %s...; code-point order gives %s... (%s)" % (
        "PASS" if ok else "FAIL", got[:12], hashlib.sha256(cp.encode()).hexdigest()[:12],
        "fixture separates the orders" if separates else "fixture does NOT separate"))
    return ok


def without(rec, drop):
    return {k: v for k, v in rec.items() if k not in drop}


def parse(text):
    rec = json.loads(text, object_pairs_hook=no_dup)
    check_ints(rec)
    return rec


def verify(text):
    """Returns [(check, ok, detail)]."""
    try:
        rec = parse(text)
    except Exception as e:
        return [("parse", False, str(e)), ("hash", False, "not run"), ("signature", False, "not run")]
    out = [("parse", True, "no duplicate keys, safe ints only")]
    ver = rec.get("canonicalization_version")
    if ver not in VERSIONS:
        why = "unknown canonicalization_version %r: no scope table, not guessing" % ver
        return out + [("hash", False, why), ("signature", False, why)]
    drop = VERSIONS[ver] + EXTRA
    hash_scope, sig_scope = HASH_SCOPE + drop, SIG_SCOPE + drop
    # Receipt: what this run actually applied, so a reader can tell which spec reading produced the PASS
    # (huilai-rushi canon_v1.6 applied_hash_scope / applied_sig_scope).
    out.append(("applied", None, "version=%r hash_scope=-%s sig_scope=-%s" % (ver, ",-".join(hash_scope), ",-".join(sig_scope))))
    got = hashlib.sha256(jcs(without(rec, hash_scope)).encode()).hexdigest()
    out.append(("hash", got == rec.get("record_sha256"), "computed %s" % got[:16]))
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(rec["ed25519_pubkey"]))
        pk.verify(bytes.fromhex(rec["signature"]), jcs(without(rec, sig_scope)).encode())
        out.append(("signature", True, "Ed25519 over JCS(record - %s)" % " - ".join(sig_scope)))
    except Exception as e:
        out.append(("signature", False, type(e).__name__ + (": " + str(e) if str(e) else "")))
    for f in drop:
        if f in rec:
            out.append(("unsigned", None, "%s = %r is outside hash AND signature: anyone can rewrite it and every check still passes" % (f, rec[f])))
    return out


def from_tc(post, comment):
    page = 1
    while page <= 10:
        url = "https://thecolony.cc/api/v1/posts/%s/comments?limit=100&page=%d" % (post, page)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
            d = json.loads(r.read())
        for c in d.get("items", []):
            if c["id"] == comment:
                m = re.search(r"```json\n(.*?)```", c["body"], re.S)
                if not m:
                    sys.exit("comment %s has no ```json block" % comment)
                return m.group(1)
        if not d.get("has_more"):
            break
        page += 1
    sys.exit("comment %s not found on post %s" % (comment, post))


def load(args):
    if args[0] == "file": return open(args[1], encoding="utf-8").read()
    if args[0] == "tc": return from_tc(args[1], args[2])
    sys.exit(__doc__)


def show(label, res):
    print("== %s" % label)
    for name, ok, detail in res:
        print("  %-10s %s  %s" % (name, {True: "PASS", False: "FAIL", None: "NOTE"}[ok], detail))
    return all(ok is not False for _, ok, _ in res)


def mutants(text):
    """Each must make at least one check FAIL. A mutant that passes means the check is dead."""
    rec = json.loads(text)
    ms = []
    def edit(label, f):
        r = json.loads(text); f(r); ms.append((label, json.dumps(r, ensure_ascii=False)))
    # first string leaf inside payload (or any top-level string field that's in the signed scope)
    def first_str(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str): return o, k
                got = first_str(v)
                if got: return got
        return None
    def flip_content(r):
        tgt = first_str(r.get("payload", r)) or first_str(without(r, SIG_SCOPE + ("ed25519_pubkey",)))
        o, k = tgt; o[k] = o[k] + "x"
    edit("content edited (one char appended)", flip_content)
    edit("signature swapped (last byte flipped)",
         lambda r: r.__setitem__("signature", r["signature"][:-2] + ("00" if r["signature"][-2:] != "00" else "01")))
    edit("hash replaced (last nibble flipped)",
         lambda r: r.__setitem__("record_sha256", r["record_sha256"][:-1] + ("0" if r["record_sha256"][-1] != "0" else "1")))
    ms.append(("duplicate key added", text.rstrip().rstrip("}") + ', "record_sha256": "%s"}' % rec["record_sha256"]))
    ms.append(("float smuggled in", text.rstrip().rstrip("}") + ', "zz_float": 1.5}'))
    # huilai-rushi canon_v1.6 scar 9 (thecolony.cc 631c7525): a record that calls itself unsigned, carries a
    # bad signature and a hash re-computed to match. Only the signature check can catch it, and the record's
    # own word about itself must not switch that check off.
    def scar9(r):
        r["signature"] = "00" * 64
        r["signature_status"] = "unsigned"
        drop = VERSIONS.get(r.get("canonicalization_version"), ())
        r["record_sha256"] = hashlib.sha256(jcs(without(r, HASH_SCOPE + drop)).encode()).hexdigest()
    edit("marked unsigned, bad signature, hash re-computed (scar 9)", scar9)
    return ms


def main(argv):
    global EXTRA
    while "--exclude" in argv:
        i = argv.index("--exclude")
        EXTRA += (argv[i + 1],)
        del argv[i:i + 2]
    if not argv: sys.exit(__doc__)
    if argv[0] == "selftest":
        text = load(argv[1:])
        order_ok = order_fixture()
        base = show("record as published", verify(text))
        dead = 0
        for label, t in mutants(text):
            ok = show("mutant: " + label, verify(t))
            if ok:
                dead += 1
                print("  ^ this mutant PASSED: a check is dead")
        print("selftest: key-order fixture %s, record %s, %d mutants, %d passed (must be 0)" % (
            "PASS" if order_ok else "FAIL", "PASS" if base else "FAIL", len(mutants(text)), dead))
        return 0 if order_ok and base and dead == 0 else 1
    return 0 if show("record", verify(load(argv))) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

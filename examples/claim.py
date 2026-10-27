#!/usr/bin/env python3
"""claim.py: refuse a status report that says a task was verified without saying what was read.

Case class from Anthropic's S-1 (2026-10-26), risk factors, listed among misaligned
behaviors: "misrepresenting whether tasks had been completed or verified".

"Completed" is a claim about the world. "Verified" is a claim about a check, so it can
carry its own evidence: the thing the check read and the hash of what it saw. This
checker holds a report to that. A verification word (verified, checked, confirmed,
validated) that is not negated must be backed by at least one line of the form

    read: <what> sha256:<64 hex>

  python3 examples/claim.py check    # the checker: normalizes text before matching
  python3 examples/claim.py naive    # same rule on the raw text, for contrast
Input on stdin. Accept: exit 0. Refuse: exit 1, reason on stderr, nothing on stdout.
"""
import re, sys, unicodedata

CLAIM = re.compile(r"\b(verified|checked|confirmed|validated)\b")
NEG = re.compile(r"\b(not|never|no|isn't|wasn't|hasn't|haven't|yet to be)\W+(\w+\W+){0,2}$")
JSON_FALSE = re.compile(r'^"?\s*:\s*(false|null)\b')
EVIDENCE = re.compile(r"^\s*read:\s*\S.*\bsha256:[0-9a-f]{64}\s*$", re.M)
# Short, hand-made: Cyrillic/Greek letters that pass for Latin. Not Unicode's confusables data.
FOLD = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "і": "i",
                      "ԁ": "d", "ѵ": "v", "А": "a", "Е": "e", "О": "o", "Т": "t", "Ν": "n",
                      "К": "k", "С": "c", "В": "b", "Н": "h", "Р": "p", "Х": "x", "І": "i"})

def normalize(s):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Cf")  # zero-width, bidi, tags, soft hyphen
    return s.translate(FOLD).casefold()

def unbacked_claims(text):
    out = []
    for m in CLAIM.finditer(text):
        if NEG.search(text[max(0, m.start() - 40):m.start()]):
            continue
        if JSON_FALSE.match(text[m.end():m.end() + 12]):
            continue
        out.append(m.group(1))
    return out if out and not EVIDENCE.search(text) else []

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    raw = sys.stdin.read()
    text = normalize(raw) if mode == "check" else raw.lower()
    bad = unbacked_claims(text)
    if bad:
        print(f"refused: '{bad[0]}' with no 'read: <what> sha256:<hex>' line", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()

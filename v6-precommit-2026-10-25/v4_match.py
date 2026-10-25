"""v4 field-match rule, copied verbatim from planted_check_v4.py (full file sha256 5774fb8a...).
Only fields() and chunks() and what they use are here. The full checker also scans our own memory
layout and gives a PASS/FAIL verdict; that wrapper is left out because it names internal paths.
The rule: a chunk links to a claim if it shares >=1 NUMBER field (>=3, or a month-day date) AND >=2
content stems (5-char prefix of words >=4 letters, stoplist removed)."""
import argparse, glob, os, re, sys
import argparse, glob, os, re, sys

FENCE = re.compile(r"<<<UNTRUSTED:[^>]*:(BEGIN|END):([^>]*)>>>")
WORD = re.compile(r"[a-z0-9]+")


NUMW = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
NUMW.update(thirty=30, forty=40, fifty=50, sixty=60, seventy=70, eighty=80, ninety=90, hundred=100, thousand=1000)
ORD = {w: i + 1 for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
       "twelfth".split())}
DAYS = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30, "year": 365, "years": 365}
STOP = set("about after again also back been before being came does down each even from have here into just like "
           "made make more most much must only over said same some still such than that their them then there "
           "these they this those very want were what when where which while will with would your note update "
           "correction record ledger heads filing small earlier".split())
DATE = re.compile(r"\b(?:20\d\d)-(\d\d)-(\d\d)\b")
CHUNK = re.compile(r"[.;!?]\s|\",\s*\"|\s[-–—]\s")


def fields(text):
    t = text.lower()
    dates = {f"d{int(m)}-{int(d)}" for m, d in DATE.findall(t)}
    t = DATE.sub(" ", t)
    t = re.sub(r"(\d+(?:\.\d+)?)k\b", lambda m: str(int(float(m.group(1)) * 1000)), t)
    w = re.findall(r"[a-z]+|\d+(?:\.\d+)?", t)
    nums = set()
    for i, x in enumerate(w):
        v = float(x) if x[0].isdigit() else NUMW.get(x, ORD.get(x))
        if v is None:
            continue
        nums.add(v)
        if i + 1 < len(w) and w[i + 1] in DAYS:
            nums.add(v * DAYS[w[i + 1]])
    stems = {x[:5] for x in w if x.isalpha() and len(x) >= 4 and x not in STOP and x not in NUMW and x not in ORD
             and x not in DAYS}
    return {n for n in nums if n >= 3 and n != 2026} | dates, stems


def chunks(ln):
    for part in CHUNK.split(ln):
        ws = part.split()
        for i in range(0, max(1, len(ws)), 40):
            yield " ".join(ws[i:i + 40])

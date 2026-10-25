"""v6 number extraction (exori, 2026-10-22). Not frozen. Replaces the v4/v5 per-token lookup.

v4 looked each token up on its own, so "twenty-eight" gave {20, 8} and never met a "28" in the claim
(gigawatt F3). Here a run of number words is read as one value:
  twenty-eight / twenty eight -> 28      one hundred and five -> 105     a hundred -> 100
  two thousand three hundred -> 2300     1.5 million / 1.5m / 2.4bn -> 1.5e6 / 2.4e9
  1,234 -> 1234      twenty-eighth -> 28      3k -> 3000
  62d / 11h / 401s / 5min / 250ms / 3x / 12% / 4th -> 62 / 11 / 401 / 5 / 250 / 3 / 12 / 4   (unit kept off the value)
Mixed letter+digit runs of 6+ chars (hashes, base58 ids: 6109bb2d, 4wtxy9na) are masked before reading, so no
digit inside an id becomes a number. Shorter mixed tokens (v4, v6n, 2fa, 10-22t05) give no number: TOKEN only
reads a digit run that starts and ends at a token edge.
The parts of a compound are NOT also emitted: emitting 20 for "twenty-eight" would link it to every "20".
"one" alone stays 1 (callers drop n < 3 anyway). "and" only joins inside a run after hundred/thousand/
million/billion ("a hundred and five"), so "three and four" stays {3, 4}.
"""
import re

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = dict(twenty=20, thirty=30, forty=40, fifty=50, sixty=60, seventy=70, eighty=80, ninety=90)
ORD_UNITS = {w: i + 1 for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth "
                                            "eleventh twelfth thirteenth fourteenth fifteenth sixteenth "
                                            "seventeenth eighteenth nineteenth".split())}
ORD_TENS = {k[:-1] + "ieth": v for k, v in TENS.items()}
SCALE = dict(hundred=100, thousand=1000, million=10**6, billion=10**9, trillion=10**12)
SUFFIX = dict(k=10**3, m=10**6, mn=10**6, b=10**9, bn=10**9)
# "second" is usually time, not an ordinal. Leave it out unless a compound ("twenty-second") needs it.
ORD_SOLO_SKIP = {"second"}

UNIT = r"(?:ms|min|st|nd|rd|th|d|h|s|x|%)"
END = r"(?![a-z0-9])"
START = r"(?<![a-z0-9])"   # no digits read out of v4, t05, 22t05: a number starts at a token edge
TOKEN = re.compile(START + r"\d+(?:,\d{3})+(?:\.\d+)?" + UNIT + "?" + END +
                   r"|" + START + r"\d+(?:\.\d+)?(?:k|mn|m|bn|b)?" + UNIT + "?" + END + r"|[a-z]+")
# a run of 6+ letters/digits holding at least one of each, unless it is a number with a unit ("1500ms" is 6)
ID = re.compile(r"(?<![a-z0-9])(?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{6,}(?![a-z0-9])")
NUMUNIT = re.compile(r"\d+(?:\.\d+)?(?:k|mn|m|bn|b)?" + UNIT + "?")


def _word_value(w):
    """(value, kind) for a single number word, kind in unit/tens/scale/ord, else None."""
    if w in UNITS:
        return UNITS[w], "unit"
    if w in TENS:
        return TENS[w], "tens"
    if w in SCALE:
        return SCALE[w], "scale"
    if w in ORD_UNITS:
        return ORD_UNITS[w], "ord"
    if w in ORD_TENS:
        return ORD_TENS[w], "ord"
    return None


def _digit_value(tok):
    # "250ms" is milliseconds, not 250 million seconds: a pure unit wins over a scale suffix
    m = re.fullmatch(r"([\d,]+(?:\.\d+)?)(?:ms|min|st|nd|rd|th|(k|mn|m|bn|b)?(?:d|h|s|x|%)?)", tok)
    v = float(m.group(1).replace(",", ""))
    return v * SUFFIX[m.group(2)] if m.group(2) else v


def tokens(text):
    t = text.lower().replace("-", " ")
    t = ID.sub(lambda m: m.group(0) if NUMUNIT.fullmatch(m.group(0)) else " ", t)
    return TOKEN.findall(t)


def numbers(text):
    """List of (value, start_token_index, end_token_index_exclusive, tokens) for every number in text.
    Hyphens are treated as spaces, so "twenty-eight" and "twenty eight" read the same."""
    toks = tokens(text)
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t[0].isdigit():
            v, j = _digit_value(t), i + 1
            if j < len(toks) and toks[j] in SCALE and toks[j] != "hundred":   # "1.5 million"
                v, j = v * SCALE[toks[j]], j + 1
            out.append((v, i, j, toks[i:j]))
            i = j
            continue
        start = i
        if t == "a" and i + 1 < len(toks) and toks[i + 1] in SCALE:      # "a hundred", "a million"
            i += 1
            t = toks[i]
        if _word_value(t) is None:
            i += 1
            continue
        if t in ORD_SOLO_SKIP:
            i += 1
            continue
        total, cur, last = 0, 0, None
        if toks[start] == "a":
            cur = 1
            last = "unit"
        while i < len(toks):
            t = toks[i]
            wv = _word_value(t)
            if t == "and" and last == "scale" and i + 1 < len(toks) and _word_value(toks[i + 1]) \
                    and _word_value(toks[i + 1])[1] in ("unit", "tens", "ord"):
                i += 1
                continue
            if wv is None:
                break
            v, kind = wv
            # a unit or tens after a unit/ord starts a new number ("three four" -> 3, 4)
            if kind in ("unit", "tens", "ord") and last in ("unit", "ord"):
                break
            if kind in ("unit", "tens", "ord") and last == "tens" and (kind == "tens" or v >= 10):
                break
            if t == "second" and last != "tens":
                break
            if kind == "scale":
                if v == 100:
                    cur = (cur or 1) * 100
                else:
                    total += (cur or 1) * v
                    cur = 0
            else:
                cur += v
            last = "ord" if kind == "ord" else kind
            i += 1
            if kind == "ord":
                break
        if i == start:
            i += 1
            continue
        out.append((total + cur, start, i, toks[start:i]))
    return out


def values(text):
    return {v for v, *_ in numbers(text)}


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:] or sys.stdin:
        print(sorted(values(line)), "<-", line.strip())

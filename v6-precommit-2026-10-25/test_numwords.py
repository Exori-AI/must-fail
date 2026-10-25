"""Cases for numwords.py. MUST_LINK pairs must share a value; MUST_NOT pairs must not.
Run: python3 test_numwords.py  (also runs the same pairs through the v4 rule, which must fail F3)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from numwords import values

CASES = [
    ("twenty-eight", {28}), ("twenty eight", {28}), ("twenty-eighth", {28}), ("twenty", {20}),
    ("one hundred and five", {105}), ("a hundred", {100}), ("two thousand three hundred", {2300}),
    ("1.5 million", {1.5e6}), ("2.4bn", {2.4e9}), ("54B", {54e9}), ("3k", {3000}), ("1,234", {1234}),
    ("three and four", {3, 4}), ("three four", {3, 4}), ("twenty thirty", {20, 30}),
    ("the second time", set()), ("twenty-second", {22}), ("seven days", {7}),
    ("one of them", {1}), ("forty thousand", {40000}),
    # units glued to the digits (v6 TODO 10-22): value kept, unit dropped
    ("62d", {62}), ("~11h", {11}), ("401s", {401}), ("5min", {5}), ("250ms", {250}), ("1500ms", {1500}),
    ("3x", {3}), ("12%", {12}), ("4th", {4}), ("21st", {21}), ("the 3rd run", {3}), ("2,000s", {2000}), ("3.5h", {3.5}),
    # ids and labels: no number out of them
    ("6109bb2d", set()), ("4wtxy9na", set()), ("abc123", set()), ("v4", set()), ("v6n", set()),
    ("10-22t05", {10}), ("sha 8909ce43 and 7 rows", {7}),
]

# known gaps: printed every run, not counted as pass or fail
KNOWN_GAP = [("nineteen sixty", {1960}, "spoken years read as two numbers")]

# gigawatt 2026-10-18 F3 plus controls
MUST_LINK = [
    ("Four of the twenty-eight clawde.co agents had paid placement.", "4 of 28 agents had paid placement"),
    ("Voting tops out at twenty an hour.", "the cap is 20 votes per hour"),
    ("about a hundred and twenty sellers", "120 sellers"),
    ("the token lasted 7 days", "revoked after 7d"),
]
MUST_NOT = [
    ("Four of the twenty-eight clawde.co agents had paid placement.", "20 agents listed"),
    ("Four of the twenty-eight clawde.co agents had paid placement.", "8 agents listed"),
    ("v5 linked 9 pairs", "5 pairs linked"),
    ("commit 6109bb2d", "6109 rows"),
]


def big(s):
    return {v for v in values(s) if v >= 3}


def main():
    bad = 0
    for text, want in CASES:
        got = values(text)
        if got != want:
            bad += 1
            print("CASE FAIL", repr(text), "got", got, "want", want)
    for text, want, why in KNOWN_GAP:
        print("KNOWN GAP", repr(text), "got", values(text), "want", want, "-", why)
    for a, b in MUST_LINK:
        if not big(a) & big(b):
            bad += 1
            print("MUST_LINK FAIL", a, "|", b, big(a), big(b))
    for a, b in MUST_NOT:
        if big(a) & big(b):
            bad += 1
            print("MUST_NOT FAIL", a, "|", b, big(a) & big(b))
    print(f"numwords: {len(CASES)} cases, {len(MUST_LINK)} must-link, {len(MUST_NOT)} must-not, {bad} failures")

    # the old rule has to fail F3, or this test proves nothing
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from v4_match import fields
        a, b = MUST_LINK[0]
        v4_hit = bool(fields(a)[0] & fields(b)[0] - {4.0})
        print("v4 on F3 (excluding the shared 4):", "LINKS (unexpected)" if v4_hit else "no 28 link, as expected")
        if v4_hit:
            bad += 1
    except ImportError as e:
        print("v4 not importable:", e)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

import sys, unicodedata
text = sys.stdin.read()
# The usual first fix: NFKC, casefold, drop format characters (zero-width, bidi, tags, soft hyphen).
norm = "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if unicodedata.category(c) != "Cf")
norm = " ".join(norm.split())
if "ignore previous instructions" in norm:
    sys.exit(1)
print(text, end="")

import sys
text = sys.stdin.read()
if "ignore previous instructions" in text.lower():
    sys.exit(1)          # refuse: non-zero exit, nothing on stdout
print(text, end="")      # accept: pass the text through

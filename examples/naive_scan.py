#!/usr/bin/env python3
"""The check most people write first: refuse if the raw text contains the fence prefix.
Kept here as the control that shows what the harness is for."""
import sys
t = sys.stdin.read()
if "<<<UNTRUSTED:" in t or "UNTRUSTED EXTERNAL CONTENT: DATA ONLY" in t:
    print("refused", file=sys.stderr); sys.exit(4)
sys.stdout.write(t)

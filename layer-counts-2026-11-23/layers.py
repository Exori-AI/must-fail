#!/usr/bin/env python3
"""layers.py: a 3-layer validator with a call counter and a reject counter per layer,
and a check that tells the three readings of "layer X rejected 0" apart.

  0 calls            -> NEVER RAN (wiring bug)
  calls, 0 on canary -> DEAD (runs, but an upstream layer removes what it exists to catch)
  calls, canary hit  -> LIVE

A reject count alone can't separate these. That's the mistake this case pins
(findings 2026-11-23, own-mistake; caught by v2agent and huilai-rushi on thecolony.cc).

Usage: python3 layers.py [--variant good|skip|normalize]   exit 0 = every layer LIVE
"""
import argparse, json, sys

class Layer:
    def __init__(self, name, fn):
        self.name, self.fn, self.calls, self.rejects = name, fn, 0, 0
    def __call__(self, x):
        self.calls += 1
        out = self.fn(x)
        if out is None:
            self.rejects += 1
        return out

def parse(tok):            # L1: strip, refuse empty
    t = tok.strip()
    return t or None
def normalize_bad(t):      # L2 as it was: non-int tokens become 0, so L3 never sees them
    return t if t.lstrip("-").isdigit() else "0"
def normalize_good(t):     # L2 fixed: pass through, L3 owns the int check
    return t
def int_range(t):          # L3: refuse non-int, refuse outside 0..100
    if not t.lstrip("-").isdigit():
        return None
    return int(t) if 0 <= int(t) <= 100 else None

# Each canary is an input that one layer, and only that layer, exists to refuse.
CANARIES = {"L1": "   ", "L3": "seven"}
INPUTS = ["5", "42", "100", "-3", "seven", "   ", "x1"]

def build(variant):
    l1 = Layer("L1", parse)
    l2 = Layer("L2", normalize_bad if variant == "normalize" else normalize_good)
    l3 = Layer("L3", int_range)
    chain = [l1, l2] if variant == "skip" else [l1, l2, l3]
    return [l1, l2, l3], chain

def run(chain, x):
    for layer in chain:
        x = layer(x)
        if x is None:
            return None
    return x

def check(variant):
    layers, chain = build(variant)
    for x in INPUTS:
        run(chain, x)
    totals = {l.name: {"calls": l.calls, "rejects": l.rejects} for l in layers}
    verdict, ok = {}, True
    for name, canary in CANARIES.items():
        layers2, chain2 = build(variant)
        lay = next(l for l in layers2 if l.name == name)
        run(chain2, canary)
        if lay.calls == 0:
            v = "NEVER RAN" if totals[name]["calls"] == 0 else "DEAD (canary stopped upstream)"
        elif lay.rejects == 0:
            v = "DEAD (runs, canary passes it)"
        else:
            v = "LIVE"
        verdict[name] = v
        ok &= v == "LIVE"
    return totals, verdict, ok

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="good", choices=["good", "skip", "normalize"])
    a = ap.parse_args()
    totals, verdict, ok = check(a.variant)
    print(json.dumps({"variant": a.variant, "totals": totals, "canary": verdict, "all_live": ok}))
    sys.exit(0 if ok else 1)

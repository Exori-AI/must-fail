#!/usr/bin/env python3
"""layers.py: a 3-layer validator with a call counter and a reject counter per layer,
and a check that tells the three readings of "layer X rejected 0" apart.

  0 calls            -> NEVER RAN (wiring bug)
  calls, 0 on canary -> DEAD (runs, but an upstream layer removes what it exists to catch)
  calls, canary hit  -> LIVE
  canary hit, but the final status doesn't name the refusal -> FIRED-UNHEARD
    (the layer refused into a log, and the run still came back green;
     case from nim on thecolony.cc: a stale mariadb config line, ERROR and
     Aborting in a helper log, install reported success)

A reject count alone can't separate these. That's the mistake this case pins
(findings 2026-11-23, own-mistake; caught by v2agent and huilai-rushi on thecolony.cc).

  canary hit, layer named, but the status still says OK -> FIRED-UNHEARD too
    (2026-11-28, cinnabar and muse-spark on thecolony.cc f62f57eb: a named refusal
     under an overall OK is heard as a fact and unheard as a verdict. The 11-27 check
     only looked for the layer's name in the status, so it called that LIVE.)

Usage: python3 layers.py [--variant good|skip|normalize|unheard|namedok]   exit 0 = every layer LIVE
"""
import argparse, json, sys

class Layer:
    def __init__(self, name, fn, log):
        self.name, self.fn, self.calls, self.rejects, self.log = name, fn, 0, 0, log
    def __call__(self, x):
        self.calls += 1
        out = self.fn(x)
        if out is None:
            self.rejects += 1
            self.log.append(f"ERROR {self.name}: refused {x!r}")
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
    log = []
    l1 = Layer("L1", parse, log)
    l2 = Layer("L2", normalize_bad if variant == "normalize" else normalize_good, log)
    l3 = Layer("L3", int_range, log)
    chain = [l1, l2] if variant == "skip" else [l1, l2, l3]
    return [l1, l2, l3], chain

def run(chain, x, variant="good"):
    """Returns the final status line, the only thing a caller reads."""
    for layer in chain:
        y = layer(x)
        if y is None:
            if variant in ("unheard", "namedok") and layer.name == "L3":
                # the helper refused, wrote to the log, and the caller carried on with a default
                if variant == "namedok":
                    return f"OK 0 (L3 refused {x!r}, used default)"
                x = "0"
                continue
            return f"REJECTED by {layer.name}: {x!r}"
        x = y
    return f"OK {x}"

def check(variant):
    layers, chain = build(variant)
    for x in INPUTS:
        run(chain, x, variant)
    totals = {l.name: {"calls": l.calls, "rejects": l.rejects} for l in layers}
    verdict, ok = {}, True
    for name, canary in CANARIES.items():
        layers2, chain2 = build(variant)
        lay = next(l for l in layers2 if l.name == name)
        status = run(chain2, canary, variant)
        if lay.calls == 0:
            v = "NEVER RAN" if totals[name]["calls"] == 0 else "DEAD (canary stopped upstream)"
        elif lay.rejects == 0:
            v = "DEAD (runs, canary passes it)"
        elif name not in status:
            # the layer fired; the refusal is in the log and not in the status anyone reads
            v = "FIRED-UNHEARD (refusal in log only, status: %s)" % status
        elif not status.startswith("REJECTED"):
            # the layer is named, but the verdict the caller acts on is still OK
            v = "FIRED-UNHEARD (named, but status is OK: %s)" % status
        else:
            v = "LIVE"
        verdict[name] = v
        ok &= v == "LIVE"
    return totals, verdict, ok

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="good", choices=["good", "skip", "normalize", "unheard", "namedok"])
    a = ap.parse_args()
    totals, verdict, ok = check(a.variant)
    print(json.dumps({"variant": a.variant, "totals": totals, "canary": verdict, "all_live": ok}))
    sys.exit(0 if ok else 1)

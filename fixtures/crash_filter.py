#!/usr/bin/env python3
"""A filter that never decides: it crashes. Each mode must score as failed rows, never as held refusals.
(langford, thecolony.cc 470b1bb9, 2026-11-26.)  usage: crash_filter.py raise|segv|exit7"""
import os, signal, sys
sys.stdin.read()
mode = sys.argv[1]
if mode == "raise":
    raise RuntimeError("model endpoint unreachable")
if mode == "segv":
    os.kill(os.getpid(), signal.SIGSEGV)
if mode == "exit7":
    sys.exit(7)

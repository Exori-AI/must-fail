#!/bin/bash
# the exact line that bit the author twice on 2026-11-05
python3 check_truth.py | tail -2; echo exit $?

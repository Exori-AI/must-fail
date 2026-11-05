#!/bin/bash
set -e
# exemption: only printf on the left (added after the same run)
printf 'abc' | ./check.sh > out.txt
echo done

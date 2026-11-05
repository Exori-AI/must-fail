#!/bin/bash
# printf exemption must not cover a real command in the middle
printf 'abc' | ./check.sh | tail -1 && echo ok

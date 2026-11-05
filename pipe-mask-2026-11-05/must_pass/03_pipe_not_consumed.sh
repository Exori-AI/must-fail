#!/bin/bash
pytest > test.log 2>&1
rc=$?
grep -c FAILED test.log | cat
tail -5 test.log
exit $rc

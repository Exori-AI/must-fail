#!/bin/bash
if make test 2>&1 | tee build.log; then
  echo ok
fi

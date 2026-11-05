#!/bin/bash
false |
  tail -1
if [ $? -eq 0 ]; then echo MASKED; fi

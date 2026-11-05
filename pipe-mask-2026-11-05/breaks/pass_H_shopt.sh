#!/bin/bash
shopt -s -o pipefail
false | tail -1 && echo MASKED

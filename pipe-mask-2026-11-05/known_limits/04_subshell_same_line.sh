#!/bin/bash
( set -o pipefail; false | tail -1 ) && echo MASKED

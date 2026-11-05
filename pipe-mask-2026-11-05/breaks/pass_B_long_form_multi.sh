#!/bin/bash
set -o errexit -o nounset -o pipefail
false | tail -1
echo MASKED

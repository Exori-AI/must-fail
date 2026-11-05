#!/bin/bash
set -e -o pipefail
npm test | grep -v WARN
echo deployed

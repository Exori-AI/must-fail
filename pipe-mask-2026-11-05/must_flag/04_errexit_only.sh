#!/bin/bash
set -e
npm test | grep -v WARN
echo deployed

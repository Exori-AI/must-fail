#!/bin/bash
set -o pipefail
ls | wc -l
set +o pipefail
go test ./... | tail -1
echo "rc=$?"

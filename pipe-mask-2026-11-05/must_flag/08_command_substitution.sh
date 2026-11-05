#!/bin/bash
out=$(go test ./... | tail -1) && echo "$out"

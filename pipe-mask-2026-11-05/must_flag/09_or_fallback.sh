#!/bin/bash
./check.sh | head -1 || echo "check failed"
echo done

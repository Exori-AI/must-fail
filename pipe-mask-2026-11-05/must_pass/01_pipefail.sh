#!/bin/bash
set -euo pipefail
pytest | tail -5
echo "tests passed"

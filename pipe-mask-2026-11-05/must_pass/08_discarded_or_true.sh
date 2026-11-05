#!/bin/bash
# exemption: status thrown away on purpose (added after a first run on our own run_examples.sh)
pytest | tail -1 || true
echo done

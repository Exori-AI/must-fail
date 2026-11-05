#!/bin/bash
# pipefail set inside a function that is never called
strict() { set -o pipefail; }
pytest | tail -5 && echo passed

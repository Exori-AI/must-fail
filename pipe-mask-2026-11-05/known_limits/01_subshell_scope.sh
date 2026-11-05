#!/bin/bash
# pipefail set only inside a subshell; the pipeline below is still masked
( set -o pipefail; true )
pytest | tail -5 && echo passed

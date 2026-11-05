#!/bin/bash
set -e
cat <<EOT > notes.txt
run: pytest | tail -5
EOT
echo done

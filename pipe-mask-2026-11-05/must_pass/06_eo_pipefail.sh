#!/bin/bash
set -eo pipefail
cargo test | tail -20

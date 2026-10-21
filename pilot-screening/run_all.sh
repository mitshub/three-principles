#!/usr/bin/env bash
# Runs the screening in dependency order. Logs go to outputs/*.log.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs
PY=.venv/bin/python
$PY -I scripts/01_wpdx.py all        2>&1 | tee outputs/01_wpdx.log
$PY -I scripts/02_boundaries_wpdx.py 2>&1 | tee outputs/02_boundaries_wpdx.log
$PY -I scripts/03_ucdp.py            2>&1 | tee outputs/03_ucdp.log
$PY -I scripts/04_overlap.py         2>&1 | tee outputs/04_overlap.log

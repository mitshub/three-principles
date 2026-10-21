#!/usr/bin/env bash
# Run every audit script in dependency order. Downloads go to data/ (git-ignored),
# derived tables to outputs/ (git-ignored). Re-runs reuse files already in data/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs
PY=".venv/bin/python -I"
export PYTHONWARNINGS=ignore
for s in 05_boundaries 01_wpdx 02a_ucdp 02b_acled 03_wealth 04_education; do
  echo "== $s"
  $PY "scripts/$s.py" > "outputs/$s.log" 2>&1 || { echo "FAILED: $s (see outputs/$s.log)"; exit 1; }
done
echo "done"

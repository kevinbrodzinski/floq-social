#!/usr/bin/env bash
set -euo pipefail
python3 rgi-ext-02g2e/verify_funded_replacement_freeze.py
python3 rgi-ext-02g2f/verify_execution_identity.py
rm -rf evidence
mkdir -p evidence
cp rgi-ext-02g2f/EXECUTION_IDENTITY.json evidence/EXECUTION_IDENTITY.json
export TARGET_BRANCH='rgi-ext-02g2f-funded-fresh-measurement-exec-20260820'
exec bash rgi-ext-02g2a/runpod_equivalence_measurement_ci.sh

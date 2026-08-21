#!/usr/bin/env bash
set -euo pipefail
python3 rgi-ext-02g2c/verify_fresh_measurement_authorization.py
python3 rgi-ext-02g2d/verify_execution_identity.py
rm -rf evidence
mkdir -p evidence
cp rgi-ext-02g2d/EXECUTION_IDENTITY.json evidence/EXECUTION_IDENTITY.json
export TARGET_BRANCH='rgi-ext-02g2d-fresh-measurement-execution-001-20260819'
exec bash rgi-ext-02g2a/runpod_equivalence_measurement_ci.sh

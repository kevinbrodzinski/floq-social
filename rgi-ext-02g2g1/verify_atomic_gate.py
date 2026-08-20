#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
f=json.loads((ROOT/'rgi-ext-02g2g1'/'ATOMIC_AVAILABILITY_TO_EXECUTION_FREEZE.json').read_text())
assert f['status']=='PROSPECTIVELY_FROZEN_BEFORE_SCHEDULE_INSTALLATION_AND_BEFORE_ANY_FUTURE_EXECUTION_IDENTITY'
assert f['availability_watch']['poll_cadence_minutes']==5
assert f['availability_watch']['provider_create_requests_before_pass']==0
assert f['availability_watch']['execution_identity_created_before_pass'] is False
assert f['hard_one_shot_consumption_lock']['lock_must_be_acquired_before_provider_create_request'] is True
assert f['hard_one_shot_consumption_lock']['provider_create_requests_after_lock']==1
assert f['hard_one_shot_consumption_lock']['provider_retry_after_create_failure'] is False
assert f['hard_one_shot_consumption_lock']['second_pod_substitution'] is False
assert f['frozen_scientific_lineage']['alpha_bootstrap_valid_draws_required_exact']==10000
assert f['parent_availability_gate']['availability_state']=='RGI_EXT_02G2G_CARRIER_UNAVAILABLE_NO_EXECUTION_AUTHORIZATION'
assert f['previous_execution_terminal']['provider_failure_cause']=='NO_INSTANCES_CURRENTLY_AVAILABLE'
executor=(ROOT/'rgi-ext-02g2'/'measurement_executor.py').read_text()
assert "if len(boot)!=10000" in executor
assert "required_bootstrap':10000" in executor
runner=(ROOT/'rgi-ext-02g2g1'/'atomic_watch_and_execute.py').read_text()
assert runner.index("if lock_exists(repo,gh)") < runner.index("availability_query(key)")
assert runner.index("availability_query(key)") < runner.index("github_json('POST',f'/repos/{repo}/git/refs'")
assert runner.index("github_json('POST',f'/repos/{repo}/git/refs'") < runner.index("runpod_equivalence_measurement_ci.sh")
assert "if not passed:" in runner
assert "return 0" in runner
assert "provider_create_requests_authorized':1" in runner
assert "provider_retry_authorized':False" in runner
assert "second_pod_substitution_authorized':False" in runner
assert "AVAILABILITY_RECEIPT_TOO_OLD_STOP_NO_PROVIDER_REQUEST" in runner
print('RGI_EXT_02G2G1_ATOMIC_GATE_STATIC_PASS')

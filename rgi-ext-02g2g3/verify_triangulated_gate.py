#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
f=json.loads((ROOT/'rgi-ext-02g2g3'/'TRIANGULATED_AVAILABILITY_GATE_FREEZE.json').read_text())
assert f['status']=='PROSPECTIVELY_FROZEN_BEFORE_SCHEDULE_INSTALLATION_AND_BEFORE_ANY_2G3_EXECUTION_IDENTITY'
assert f['triangulated_pass_rule']['gpu_type_id_exact']=='NVIDIA RTX A4000'
assert f['triangulated_pass_rule']['runpodctl_gpu_available_exact'] is True
assert f['triangulated_pass_rule']['runpodctl_secure_cloud_exact'] is True
assert f['triangulated_pass_rule']['runpodctl_secure_price_per_hr_non_null'] is True
assert f['triangulated_pass_rule']['runpodctl_aggregate_stock_status_allowed']==['Low','Medium','High']
assert f['triangulated_pass_rule']['graphql_available_gpu_counts_role']=='RECORDED_DIAGNOSTIC_ONLY_NOT_A_PASS_CRITERION'
assert f['hard_one_shot_consumption_lock']['lock_ref']=='refs/heads/rgi-ext-02g2g1-atomic-consumed'
assert f['hard_one_shot_consumption_lock']['provider_create_requests_after_lock']==1
assert f['hard_one_shot_consumption_lock']['provider_retry_after_create_failure'] is False
assert f['hard_one_shot_consumption_lock']['second_pod_substitution'] is False
assert f['frozen_scientific_lineage']['alpha_bootstrap_valid_draws_required_exact']==10000
executor=(ROOT/'rgi-ext-02g2'/'measurement_executor.py').read_text()
assert "if len(boot)!=10000" in executor
runner=(ROOT/'rgi-ext-02g2g3'/'triangulated_watch_and_execute.py').read_text()
assert "if lock_exists(repo,gh)" in runner
assert "gpu','list','--include-unavailable'" in runner
assert "datacenter','list'" in runner
assert "available_true" in runner
assert "secure_cloud_true" in runner
assert "secure_price_non_null" in runner
assert "aggregate_stock_positive" in runner
assert "datacenter_stock_positive" in runner
assert "graphql_available_gpu_counts_role':'DIAGNOSTIC_ONLY'" in runner
assert runner.index("if lock_exists(repo,gh)") < runner.index("run_json([runpodctl,'gpu','list','--include-unavailable'])")
assert runner.index("if not passed:") < runner.index("github_json('POST',f'/repos/{repo}/git/refs'")
assert runner.index("github_json('POST',f'/repos/{repo}/git/refs'") < runner.index("runpod_equivalence_measurement_ci.sh")
assert "provider_create_requests_authorized':1" in runner
assert "provider_retry_authorized':False" in runner
assert "second_pod_substitution_authorized':False" in runner
assert "AVAILABILITY_RECEIPT_TOO_OLD_STOP_NO_PROVIDER_REQUEST" in runner
print('RGI_EXT_02G2G3_TRIANGULATED_GATE_STATIC_PASS')

#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
AUTH=ROOT/'rgi-ext-02g2c'/'FRESH_MEASUREMENT_EXECUTION_AUTHORIZATION.json'
MEAS=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
AMEND=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
REPAIR=ROOT/'rgi-ext-02g2b'/'MEASUREMENT_INSTRUMENTATION_REPAIR_FREEZE.json'
WORKER=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'
SCHEMA=ROOT/'rgi-ext-02g2b'/'schema_contract_test.py'
VERIFY_REPAIR=ROOT/'rgi-ext-02g2b'/'verify_repair_freeze.py'
REPAIR_WF=ROOT/'.github/workflows/rgi-ext-02g2b-repair-freeze.yml'
EXECUTOR=ROOT/'rgi-ext-02g2a'/'measurement_executor_equiv.py'

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git_blob_sha(p):
    b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def main():
    a=json.loads(AUTH.read_text())
    assert a['experiment_id']=='RGI-EXT-02G.2c'
    assert a['fresh_measurement_identity']=='RGI-EXT-02G.2c-FRESH-MEASUREMENT-001'
    assert a['status']=='PROSPECTIVELY_FROZEN_PENDING_FINAL_SOURCE_CONFIG_PREFLIGHT'
    z=a['zero_observation_custody']
    assert z['successor_observation_count_at_authorization_freeze']==0
    assert z['successor_alpha_grid_points_collected']==0
    assert z['successor_warmup_points_collected']==0
    assert z['successor_retained_points_collected']==0
    assert z['successor_dataset_must_begin_empty'] is True
    for k in ['successor_alpha_estimated','successor_beta_applied','successor_theta_computed','successor_class_assigned','successor_blind_holdout_collected','successor_boundary_contact_H_seen','successor_boundary_contact_K_seen']:
        assert z[k] is False
    c=a['pr10_contamination_exclusion']
    assert c['classification']=='NON_REUSABLE_FAILURE_DIAGNOSTIC_CONTAMINATION_EVIDENCE'
    for k in ['may_enter_successor_dataset','may_enter_alpha_fit','may_enter_bootstrap','may_influence_parameter_selection','may_influence_ordering','may_influence_thresholds','may_be_replayed_as_successor_measurement']:
        assert c[k] is False
    e=a['execution_boundary']
    assert e['gpu_provisioning_authorized_now'] is False
    assert e['scientific_measurement_authorized_now'] is False
    assert e['final_preflight_must_be_no_gpu'] is True
    assert e['final_preflight_must_not_send_provider_create_request'] is True
    assert e['final_preflight_must_not_collect_scientific_response'] is True
    assert sha256(MEAS)==a['frozen_scientific_lineage']['measurement_admissibility_sha256']=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
    assert sha256(AMEND)==a['frozen_scientific_lineage']['carrier_equivalence_amendment_sha256']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
    b=a['parent_repair_freeze']['cryptographic_bindings']
    assert git_blob_sha(REPAIR)==b['repair_freeze_git_blob_sha1']=='b9521f4acd9e0c9ead6c1425375efc153e6bdbf8'
    assert git_blob_sha(SCHEMA)==b['schema_contract_test_git_blob_sha1']=='4cf372482b097eaff98904545ed190f719ed1977'
    assert git_blob_sha(VERIFY_REPAIR)==b['repair_verifier_git_blob_sha1']=='8e4dccc76e2cd3891d20f1dcaa231494fd824aca'
    assert git_blob_sha(WORKER)==b['repaired_point_worker_git_blob_sha1']=='b0d201e992438dfb7ca8857b9a101b30d088843c'
    assert git_blob_sha(REPAIR_WF)==b['repair_freeze_workflow_git_blob_sha1']=='a33cb8df6a5724731de6754c37e33fc11314c8bc'
    worker=WORKER.read_text(); executor=EXECUTOR.read_text()
    assert "'thermal_or_hw_slowdown_active':active" in worker
    assert "'slowdown_evidence':evidence" in worker
    assert "obj['pressure_pre_snapshot']['thermal_or_hw_slowdown_active']" in executor
    assert "obj['pressure_post_snapshot']['thermal_or_hw_slowdown_active']" in executor
    print('RGI_EXT_02G2C_FINAL_SOURCE_CONFIG_PREFLIGHT_PASS')

if __name__=='__main__': main()

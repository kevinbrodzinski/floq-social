#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
AUTH=ROOT/'rgi-ext-02g2e'/'FUNDED_PREOBSERVATION_REPLACEMENT_AUTHORIZATION.json'
MEAS=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
AMEND=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
EXECUTOR=ROOT/'rgi-ext-02g2'/'measurement_executor.py'
WORKER=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    a=json.loads(AUTH.read_text())
    assert a['experiment_id']=='RGI-EXT-02G.2e'
    assert a['status']=='PROSPECTIVELY_FROZEN_BEFORE_ANY_NEW_PROVIDER_CREATE_REQUEST'
    p=a['parent_terminal_execution']
    assert p['pr']==13 and p['workflow_run_id']==32334127909
    assert p['terminal_state']=='PRE_OBSERVATION_PROVIDER_CREATE_FAILURE_STOP_NO_FURTHER_RETRY'
    assert p['stage']=='RUNPOD_CREATE' and p['http_status']==500
    assert p['provider_failure_cause']=='ACCOUNT_BALANCE_TOO_LOW'
    assert p['pod_id_issued'] is False and p['gpu_observed'] is False
    assert p['carrier_equivalence_preflight_started'] is False and p['scientific_measurement_started'] is False
    assert p['successor_observation_count']==0
    assert a['funding_condition']['user_confirmed_runpod_funded'] is True
    assert sha256(MEAS)==a['frozen_lineage']['measurement_admissibility_sha256']=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
    assert sha256(AMEND)==a['frozen_lineage']['carrier_equivalence_amendment_sha256']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
    assert a['zero_observation_custody']['successor_observation_count_before_replacement']==0
    assert a['authorization_boundary']['provider_create_requests_authorized_by_this_freeze']==0
    assert a['authorization_boundary']['after_required_zero_cost_gate_only']['provider_create_requests_authorized']==1
    src=EXECUTOR.read_text()
    assert 'for _ in range(10000):' in src
    assert "if len(boot)!=10000:return None" in src
    assert "'required_bootstrap':10000" in src
    assert '<9500' not in src
    worker=WORKER.read_text()
    assert "'thermal_or_hw_slowdown_active':active" in worker
    assert "'slowdown_evidence':evidence" in worker
    print('RGI_EXT_02G2E_FUNDED_REPLACEMENT_PREFLIGHT_PASS')

if __name__=='__main__': main()

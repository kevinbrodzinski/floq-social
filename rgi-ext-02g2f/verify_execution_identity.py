#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
ID=ROOT/'rgi-ext-02g2f'/'EXECUTION_IDENTITY.json'
AUTH=ROOT/'rgi-ext-02g2e'/'FUNDED_PREOBSERVATION_REPLACEMENT_AUTHORIZATION.json'
EXECUTOR=ROOT/'rgi-ext-02g2'/'measurement_executor.py'

def main():
    i=json.loads(ID.read_text()); a=json.loads(AUTH.read_text())
    assert i['experiment_id']=='RGI-EXT-02G.2f'
    assert i['execution_identity']=='RGI-EXT-02G.2f-FUNDED-FRESH-MEASUREMENT-001-EXECUTION-001'
    assert i['fresh_measurement_identity']=='RGI-EXT-02G.2c-FRESH-MEASUREMENT-001'
    assert i['parent_funded_replacement_freeze']['preflight_workflow_run_id']==32345347281
    assert i['parent_funded_replacement_freeze']['required_pass_marker']=='RGI_EXT_02G2E_FUNDED_REPLACEMENT_PREFLIGHT_PASS'
    assert i['parent_failed_execution']['pr']==13
    assert i['parent_failed_execution']['pod_id_issued'] is False
    assert i['parent_failed_execution']['scientific_measurement_started'] is False
    assert i['parent_failed_execution']['successor_observations']==0
    e=i['execution_authority']
    assert e['provider_create_requests_authorized']==1
    assert e['no_second_pod_substitution'] is True
    assert e['no_provider_retry'] is True
    assert e['no_manual_parallel_provisioning'] is True
    assert e['delete_pod_on_every_terminal_path'] is True
    assert a['authorization_boundary']['required_zero_cost_gate']=='RGI_EXT_02G2E_FUNDED_REPLACEMENT_PREFLIGHT_PASS'
    src=EXECUTOR.read_text()
    assert 'for _ in range(10000):' in src
    assert 'if len(boot)!=10000:return None' in src
    print('RGI_EXT_02G2F_EXECUTION_IDENTITY_PASS')

if __name__=='__main__': main()

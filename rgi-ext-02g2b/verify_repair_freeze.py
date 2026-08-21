#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
FREEZE=ROOT/'rgi-ext-02g2b'/'MEASUREMENT_INSTRUMENTATION_REPAIR_FREEZE.json'
WORKER=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'
MEAS=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
AMEND=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
SCHEMA=ROOT/'rgi-ext-02g2b'/'schema_contract_test.py'

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git_blob_sha(p):
    b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def main():
    f=json.loads(FREEZE.read_text())
    assert f['experiment_id']=='RGI-EXT-02G.2b'
    assert f['status']=='PROSPECTIVELY_FROZEN_BEFORE_ANY_NEW_GPU_PROVISIONING'
    assert f['authorization_boundary']['new_gpu_provisioning_authorized_by_this_freeze'] is False
    assert f['authorization_boundary']['scientific_measurement_authorized_by_this_freeze'] is False
    assert f['authorization_boundary']['no_rerun_of_pr10'] is True
    assert f['contamination_custody']['non_reusable'] is True
    assert f['contamination_custody']['must_not_enter_successor_dataset'] is True
    assert f['contamination_custody']['must_not_enter_alpha_fit'] is True
    assert f['contamination_custody']['must_not_enter_bootstrap'] is True
    assert sha256(MEAS)==f['frozen_parent_contracts']['measurement_admissibility_sha256']=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
    assert sha256(AMEND)==f['frozen_parent_contracts']['carrier_equivalence_amendment_sha256']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
    assert git_blob_sha(WORKER)==f['authorized_repair']['worker_git_blob_sha_after_repair']=='b0d201e992438dfb7ca8857b9a101b30d088843c'
    src=WORKER.read_text()
    assert "'thermal_or_hw_slowdown_active':active" in src
    assert "'slowdown_evidence':evidence" in src
    p=subprocess.run([sys.executable,str(SCHEMA)],text=True,capture_output=True)
    assert p.returncode==0, p.stderr+p.stdout
    assert 'RGI_EXT_02G2B_SCHEMA_CONTRACT_PASS' in p.stdout
    print('RGI_EXT_02G2B_REPAIR_FREEZE_PASS')

if __name__=='__main__': main()

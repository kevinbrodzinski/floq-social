#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
IDENT=ROOT/'rgi-ext-02g2d'/'EXECUTION_IDENTITY.json'
AUTH=ROOT/'rgi-ext-02g2c'/'FRESH_MEASUREMENT_EXECUTION_AUTHORIZATION.json'
AUTHV=ROOT/'rgi-ext-02g2c'/'verify_fresh_measurement_authorization.py'
AUTHW=ROOT/'.github/workflows/rgi-ext-02g2c-authorization-preflight.yml'
REPAIR=ROOT/'rgi-ext-02g2b'/'MEASUREMENT_INSTRUMENTATION_REPAIR_FREEZE.json'
WORKER=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'
MEAS=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
AMEND=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def main():
 x=json.loads(IDENT.read_text())
 assert x['experiment_id']=='RGI-EXT-02G.2d'
 assert x['execution_identity']=='RGI-EXT-02G.2d-FRESH-MEASUREMENT-001-EXECUTION-001'
 assert x['fresh_measurement_identity']=='RGI-EXT-02G.2c-FRESH-MEASUREMENT-001'
 assert x['status']=='PROSPECTIVELY_BOUND_BEFORE_ONE_SHOT_PROVISIONING'
 p=x['parent_authorization']
 assert p['head_sha']=='4f22b9451a665f6266153a7de9b335018ad6ae3b'
 assert p['preflight_workflow_run_id']==32333873662 and p['preflight_workflow_job_id']==96319534834
 assert p['preflight_conclusion']=='success' and p['required_pass_marker']=='RGI_EXT_02G2C_FINAL_SOURCE_CONFIG_PREFLIGHT_PASS'
 assert blob(AUTH)==p['authorization_blob_sha1']=='f17a707e16ffd493c01e1caddf5655f598eafc08'
 assert blob(AUTHV)==p['authorization_verifier_blob_sha1']=='84519751e82b75813038cc5205a3db86d2b497cc'
 assert blob(AUTHW)==p['authorization_workflow_blob_sha1']=='30ff8932a6207d18b1e48e9070a2aef12a7f2ab9'
 f=x['frozen_lineage']
 assert sha256(MEAS)==f['measurement_admissibility_sha256']=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
 assert sha256(AMEND)==f['carrier_equivalence_amendment_sha256']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
 assert blob(REPAIR)==f['repair_freeze_blob_sha1']=='b9521f4acd9e0c9ead6c1425375efc153e6bdbf8'
 assert blob(WORKER)==f['repaired_point_worker_blob_sha1']=='b0d201e992438dfb7ca8857b9a101b30d088843c'
 e=x['execution_authority']
 assert e['provider_create_requests_authorized']==1
 for k in ['fresh_carrier_equivalence_preflight_required','scientific_sweep_only_after_equivalence_certification','no_second_pod_substitution','no_outcome_dependent_retry','no_parameter_retuning','no_scientific_design_change']:
  assert e[k] is True
 assert x['zero_start']['successor_observations_before_execution']==0
 assert x['zero_start']['successor_dataset_must_start_empty'] is True
 assert x['zero_start']['pr10_measurement_reuse_forbidden'] is True
 print('RGI_EXT_02G2D_EXECUTION_IDENTITY_PASS')
if __name__=='__main__': main()

#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=Path(__file__).with_name('PREOBSERVATION_TRANSPORT_RETRY_FREEZE.json')
A=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
F=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads(P.read_text())
assert p['status']=='PROSPECTIVELY_FROZEN_BEFORE_REPLACEMENT_CREATE_REQUEST'
assert sha(F)==p['frozen_parent_contracts']['measurement_admissibility_sha256']=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
assert sha(A)==p['frozen_parent_contracts']['carrier_equivalence_amendment_sha256']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
pe=p['parent_execution']
assert pe['workflow_run_id']==32330871357 and pe['provider_result']=='HTTP_500'
assert pe['pod_id_issued'] is False and pe['gpu_provisioned'] is False and pe['gpu_identity_observed'] is False
assert pe['carrier_equivalence_preflight_started'] is False and pe['scientific_measurement_started'] is False
r=p['retry_admissibility'];assert r['replacement_create_requests_authorized']==1
assert r['admissible_pre_observation_failure']['http_status_family']=='5xx'
assert all(r['admissible_pre_observation_failure'][k] is True for k in ['pod_id_must_be_absent','gpu_hardware_observation_must_be_absent','carrier_equivalence_certificate_must_be_absent','scientific_measurement_must_be_absent'])
assert r['carrier_equivalence_contract']=='UNCHANGED' and r['scientific_measurement_contract']=='UNCHANGED'
assert r['no_parameter_retuning'] is True and r['no_gpu_type_substitution'] is True and r['no_response_dependent_change'] is True
for k,v in p['custody'].items():assert v is False,(k,v)
print('RGI_EXT_02G2A1_PREOBSERVATION_RETRY_FREEZE_PASS')

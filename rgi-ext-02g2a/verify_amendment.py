#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=Path(__file__).with_name('CARRIER_EQUIVALENCE_AMENDMENT.json')
F=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
R=ROOT/'rgi-ext-02g2'/'EXT02G1_SUCCESSFUL_CARRIER_RECEIPT.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads(A.read_text()); f=json.loads(F.read_text()); r=json.loads(R.read_text())
assert sha(F)=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
assert sha(R)=='813b24ff0f6fe2d84df30110c2b5be8a36e3ee333c9ca0ad98a0aa458c4e5a9a'
assert a['status']=='PROSPECTIVELY_FROZEN_BEFORE_NEW_GPU_PROVISIONING'
assert a['parent_freeze']['failed_terminal_state']=='GPU_IDENTITY_MISMATCH_STOP_NO_MEASUREMENT'
assert a['parent_freeze']['failed_run_scientific_measurement_crossed'] is False
req=a['carrier_equivalence_class']['requirements']
assert req['device_name_exact']=='NVIDIA RTX A4000'
assert req['compute_capability_exact']==[8,6]
assert req['native_capacity_bytes_exact']==16883908608
assert req['nvidia_smi_capacity_mib_exact']==16376
assert req['native_quantum_bytes_exact']==2097152
assert req['resource_coordinate_exact']=='GPU_DEVICE_MEMORY_FRACTION'
assert req['gpu_count_exact']==1 and req['mig_or_partitioning_allowed'] is False
assert req['container_image_exact']=='runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04'
assert req['cuda_python_exact']=='11.8.3' and req['cuda_runtime_family']=='11.8'
assert req['input_dtype_exact']=='torch.float32' and req['matmul_shape_exact']==[1024,1024] and req['seed_exact']==260819
assert a['carrier_equivalence_class']['physical_uuid_role']=='PROVENANCE_ONLY_NOT_ADMISSION_CRITERION'
assert a['preflight_protocol']['provisioning_attempts_authorized']==1
assert a['preflight_protocol']['no_scientific_response_measurement_before_equivalence_pass'] is True
assert a['preflight_protocol']['no_retry_or_substitution_after_failure_under_this_amendment'] is True
for k,v in a['custody'].items(): assert v is False,(k,v)
# The original science remains frozen and UUID remains present only in the parent profile.
assert f['resource_coordinate']['id']=='GPU_DEVICE_MEMORY_FRACTION'
assert len(f['alpha_measurement_grid']['requested_p'])==15
assert r['identity']['device_name']=='NVIDIA RTX A4000'
assert r['workload']['payload']['compute_capability']==[8,6]
assert r['workload']['payload']['native_capacity_bytes']==16883908608
assert r['native_quantum']['quantum']==2097152
print('RGI_EXT_02G2A_AMENDMENT_STATIC_FREEZE_PASS')

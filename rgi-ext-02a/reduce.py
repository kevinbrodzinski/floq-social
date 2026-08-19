#!/usr/bin/env python3
import json,hashlib,platform,time
from pathlib import Path

def load(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
x=load('pre-x64/pre-x64.json'); a=load('pre-arm64/pre-arm64.json'); e=load('eval/RGI_EXT_02A_EVALUATOR_RECEIPT.json'); px=load('post-x64/post-x64.json'); pa=load('post-arm64/post-arm64.json')
checks={
 'x64_blackbox':x['status']=='PASS',
 'arm64_blackbox':a['status']=='PASS',
 'same_profile':x['profile_sha256']==a['profile_sha256']==e['profile_sha256'],
 'x64_real_vector':x['state']['extensions']['org.resourcegeometry.ext02a']['native_vector_result']['elapsed_ns']>0,
 'arm64_real_vector':a['state']['extensions']['org.resourcegeometry.ext02a']['native_vector_result']['elapsed_ns']>0,
 'heterogeneous_architecture':x['architecture']=='x86_64' and a['architecture']=='arm64',
 'both_unknown':x['state']['status']=='UNKNOWN' and a['state']['status']=='UNKNOWN',
 'no_numeric_brodzinski':'brodzinski' not in x['state'] and 'brodzinski' not in a['state'],
 'typed_reason':x['state']['reason']['code']=='MEASUREMENT_NOT_EXECUTED' and a['state']['reason']['code']=='MEASUREMENT_NOT_EXECUTED',
 'evaluator':e['result']=='REAL_HARDWARE_TYPED_REFUSAL_INTEROPERABILITY_PASS',
 'fresh_x64_reverification':px['status']=='PASS',
 'fresh_arm64_reverification':pa['status']=='PASS'
}
result='REAL_HARDWARE_INTEROPERABILITY_TYPED_REFUSAL_PASS' if all(checks.values()) else 'FAIL'
receipt={'trial':'RGI-EXT-02A','result':result,'profile_sha256':e['profile_sha256'],'checks':checks,'targets':{'x64':{'state_id':x['state']['state_id'],'kernel':x['state']['extensions']['org.resourcegeometry.ext02a']['native_kernel'],'environment_sha256':x['state']['extensions']['org.resourcegeometry.ext02a']['environment_sha256']},'arm64':{'state_id':a['state']['state_id'],'kernel':a['state']['extensions']['org.resourcegeometry.ext02a']['native_kernel'],'environment_sha256':a['state']['extensions']['org.resourcegeometry.ext02a']['environment_sha256']}},'artifact_sha256':{'pre_x64':sha('pre-x64/pre-x64.json'),'pre_arm64':sha('pre-arm64/pre-arm64.json'),'evaluator':sha('eval/RGI_EXT_02A_EVALUATOR_RECEIPT.json'),'post_x64':sha('post-x64/post-x64.json'),'post_arm64':sha('post-arm64/post-arm64.json')},'reducer_environment':{'platform':platform.platform(),'machine':platform.machine(),'reduced_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},'claim_boundary':'Real heterogeneous hosted hardware and public RGI typed-refusal semantics are demonstrated. Numeric Resource Geometry, a Brodzinski Number, Tier-3 state certification, discrete-GPU execution, and independent organizational operation are not demonstrated.'}
Path('RGI_EXT_02A_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
Path('RGI_EXT_02A_REPORT.md').write_text(f"# RGI-EXT-02A Real Heterogeneous Hardware Interoperability\n\nResult: **{result}**\n\nProfile SHA-256: `{e['profile_sha256']}`\n\nTarget x64 kernel: `{receipt['targets']['x64']['kernel']}`; state: `UNKNOWN`.\n\nTarget arm64 kernel: `{receipt['targets']['arm64']['kernel']}`; state: `UNKNOWN`.\n\nBoth targets executed native hardware vector kernels but emitted no Brodzinski Number because the target-specific alpha/beta measurement instrument is not validated.\n\nClaim boundary: {receipt['claim_boundary']}\n")
print(json.dumps(receipt,indent=2,sort_keys=True));raise SystemExit(0 if result.endswith('_PASS') else 2)

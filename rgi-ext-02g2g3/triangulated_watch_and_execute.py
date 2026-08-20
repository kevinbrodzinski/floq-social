#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

GPU='NVIDIA RTX A4000'
DOMAIN='RGI-EXT-02G.2g.3|TRIANGULATED-EXECUTION-IDENTITY|v1'
LOCK_BRANCH='rgi-ext-02g2g1-atomic-consumed'
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'
ALLOWED={'Low','Medium','High'}

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def write_json(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')

def github_json(method,path,token,payload=None):
    url='https://api.github.com'+path
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method=method,headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(); return r.status,(json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw=e.read()
        try: obj=json.loads(raw) if raw else {}
        except Exception: obj={'message':'unparseable github response'}
        return e.code,obj

def lock_exists(repo,token):
    code,_=github_json('GET',f'/repos/{repo}/git/ref/heads/{LOCK_BRANCH}',token)
    if code==200:return True
    if code==404:return False
    raise SystemExit(f'LOCK_LOOKUP_FAILED_HTTP_{code}')

def gql_diag(key):
    q='query { gpuTypes(input: { id: "NVIDIA RTX A4000" }) { id displayName lowestPrice(input: { gpuCount: 1, secureCloud: true }) { stockStatus uninterruptablePrice availableGpuCounts } } }'
    url='https://api.runpod.io/graphql?'+urllib.parse.urlencode({'api_key':key})
    req=urllib.request.Request(url,data=json.dumps({'query':q}).encode(),headers={'Content-Type':'application/json','User-Agent':'rgi-ext-02g2g3-triangulated-gate/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as r: raw=r.read(); status=r.status
    except urllib.error.HTTPError as e: raw=e.read(); status=e.code
    try: obj=json.loads(raw)
    except Exception: obj={'errors':[{'message':'NON_JSON_PROVIDER_RESPONSE'}]}
    rows=(obj.get('data') or {}).get('gpuTypes') or [] if isinstance(obj,dict) else []
    gpu=next((x for x in rows if x.get('id')==GPU),None)
    return {'http_status':status,'gpu_result':gpu,'errors':obj.get('errors') if isinstance(obj,dict) else None}

def run_json(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    if p.returncode!=0:
        return p.returncode,None,p.stderr[-2000:]
    try: return p.returncode,json.loads(p.stdout),p.stderr[-2000:]
    except Exception: return p.returncode,None,'NON_JSON_RUNPODCTL_OUTPUT:'+p.stdout[-1000:]

def main():
    key=os.environ['RUNPOD_API']; gh=os.environ['GITHUB_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']
    freeze_sha=os.environ['TRIANGULATED_FREEZE_COMMIT_SHA']
    expected_branch=os.environ['TRIANGULATED_SOURCE_BRANCH']
    runpodctl=os.environ['RUNPODCTL']
    if lock_exists(repo,gh):
        print('RGI_EXT_02G2G3_ALREADY_CONSUMED_STOP_NO_INVENTORY_QUERY_NO_PROVIDER_REQUEST'); return 0
    EVIDENCE.mkdir(exist_ok=True)
    gpu_rc,gpus,gpu_err=run_json([runpodctl,'gpu','list','--include-unavailable'])
    dc_rc,dcs,dc_err=run_json([runpodctl,'datacenter','list'])
    diag=gql_diag(key)
    exact=next((x for x in (gpus or []) if x.get('gpuId')==GPU),None) if isinstance(gpus,list) else None
    dc_hits=[]
    for dc in dcs or []:
        for x in dc.get('gpuAvailability') or []:
            if x.get('gpuId')==GPU:
                dc_hits.append({'dataCenterId':dc.get('id'),'location':dc.get('location'),'stockStatus':x.get('stockStatus')})
    predicates={
      'runpodctl_commands_ok':gpu_rc==0 and dc_rc==0,
      'exact_gpu_present':bool(exact and exact.get('gpuId')==GPU),
      'available_true':bool(exact and exact.get('available') is True),
      'secure_cloud_true':bool(exact and exact.get('secureCloud') is True),
      'secure_price_non_null':bool(exact and exact.get('securePricePerHr') is not None),
      'aggregate_stock_positive':bool(exact and exact.get('stockStatus') in ALLOWED),
      'datacenter_stock_positive':any(x.get('stockStatus') in ALLOWED for x in dc_hits)
    }
    query_error=not predicates['runpodctl_commands_ok']
    passed=(not query_error) and all(v for k,v in predicates.items() if k!='runpodctl_commands_ok')
    if query_error: state='RGI_EXT_02G2G3_AVAILABILITY_QUERY_ERROR_NO_EXECUTION_AUTHORIZATION'
    elif passed: state='RGI_EXT_02G2G3_CARRIER_AVAILABLE'
    else: state='RGI_EXT_02G2G3_CARRIER_UNAVAILABLE_NO_EXECUTION_AUTHORIZATION'
    receipt={'artifact_type':'RGI_EXT_02G2G3_TRIANGULATED_AVAILABILITY_RECEIPT','experiment_id':'RGI-EXT-02G.2g.3','queried_at_ns':time.time_ns(),'operation_type':'READ_ONLY_PROVIDER_NATIVE_TRIANGULATION','state':state,'availability_passed':passed,'predicates':predicates,'runpodctl_gpu_result':exact,'runpodctl_datacenter_hits':dc_hits,'runpodctl_gpu_returncode':gpu_rc,'runpodctl_gpu_error':gpu_err,'runpodctl_datacenter_returncode':dc_rc,'runpodctl_datacenter_error':dc_err,'graphql_secure_diagnostic':diag,'graphql_available_gpu_counts_role':'DIAGNOSTIC_ONLY','provider_create_request_sent':False,'pod_created':False,'scientific_measurement_started':False,'triangulated_freeze_commit_sha':freeze_sha}
    receipt['receipt_sha256']=sha256_bytes(canon(receipt)); write_json(EVIDENCE/'AVAILABILITY_RECEIPT.json',receipt)
    if not passed:
        print(json.dumps({'state':state,'availability_passed':False,'predicates':predicates,'receipt_sha256':receipt['receipt_sha256']},sort_keys=True)); return 0
    f=json.loads((ROOT/'rgi-ext-02g2g3'/'TRIANGULATED_AVAILABILITY_GATE_FREEZE.json').read_text())
    fields=[DOMAIN,receipt['receipt_sha256'],freeze_sha,f['frozen_scientific_lineage']['measurement_admissibility_sha256'],f['frozen_scientific_lineage']['carrier_equivalence_amendment_sha256'],f['frozen_scientific_lineage']['repair_freeze_head_sha'],f['frozen_scientific_lineage']['fresh_authorization_head_sha'],f['frozen_scientific_lineage']['fresh_measurement_identity']]
    identity_hash=hashlib.sha256('|'.join(fields).encode()).hexdigest(); execution_identity='RGI-EXT-02G.2g.3-EXEC-'+identity_hash[:24]
    age_seconds=(time.time_ns()-receipt['queried_at_ns'])/1e9
    if age_seconds>120: raise SystemExit('AVAILABILITY_RECEIPT_TOO_OLD_STOP_NO_PROVIDER_REQUEST')
    code,_=github_json('POST',f'/repos/{repo}/git/refs',gh,{'ref':f'refs/heads/{LOCK_BRANCH}','sha':freeze_sha})
    if code!=201:
        if code==422:
            print('RGI_EXT_02G2G3_LOCK_ALREADY_CONSUMED_STOP_NO_PROVIDER_REQUEST'); return 0
        raise SystemExit(f'LOCK_ACQUISITION_FAILED_HTTP_{code}_STOP_NO_PROVIDER_REQUEST')
    authorization={'artifact_type':'RGI_EXT_02G2G3_DETERMINISTIC_EXECUTION_AUTHORIZATION','experiment_id':'RGI-EXT-02G.2g.3','execution_identity':execution_identity,'identity_sha256':identity_hash,'availability_receipt_sha256':receipt['receipt_sha256'],'availability_state':state,'triangulated_freeze_commit_sha':freeze_sha,'source_branch':expected_branch,'lock_ref':f'refs/heads/{LOCK_BRANCH}','lock_acquired':True,'lock_acquired_at_ns':time.time_ns(),'provider_create_requests_authorized':1,'provider_retry_authorized':False,'second_pod_substitution_authorized':False,'scientific_design_change':False,'pr10_data_reuse_authorized':False}
    authorization['authorization_sha256']=sha256_bytes(canon(authorization)); write_json(EVIDENCE/'EXECUTION_AUTHORIZATION.json',authorization)
    env=os.environ.copy(); env['TARGET_BRANCH']=expected_branch
    p=subprocess.run(['bash',str(ROOT/'rgi-ext-02g2a'/'runpod_equivalence_measurement_ci.sh')],cwd=ROOT,env=env)
    return p.returncode

if __name__=='__main__': raise SystemExit(main())

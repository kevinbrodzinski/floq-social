#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

GPU='NVIDIA RTX A4000'
QUERY='query { gpuTypes(input: { id: "NVIDIA RTX A4000" }) { id displayName lowestPrice(input: { gpuCount: 1, secureCloud: true }) { stockStatus uninterruptablePrice availableGpuCounts } } }'
DOMAIN='RGI-EXT-02G.2g.1|ATOMIC-EXECUTION-IDENTITY|v1'
LOCK_BRANCH='rgi-ext-02g2g1-atomic-consumed'
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'

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

def availability_query(key):
    url='https://api.runpod.io/graphql?'+urllib.parse.urlencode({'api_key':key})
    req=urllib.request.Request(url,data=json.dumps({'query':QUERY}).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(); status=r.status
    except urllib.error.HTTPError as e:
        status=e.code; raw=e.read()
    try: obj=json.loads(raw)
    except Exception: obj={'errors':[{'message':'unparseable provider response'}]}
    if status!=200 or obj.get('errors'):
        return status,None,False,obj.get('errors') or [{'message':f'HTTP_{status}'}]
    rows=(obj.get('data') or {}).get('gpuTypes') or []
    gpu=next((x for x in rows if x.get('id')==GPU),None)
    lp=(gpu or {}).get('lowestPrice') or {}
    stock=lp.get('stockStatus'); counts=lp.get('availableGpuCounts') or []; price=lp.get('uninterruptablePrice')
    passed=(stock not in (None,'None') and 1 in counts and price is not None)
    return status,gpu,passed,None

def main():
    key=os.environ['RUNPOD_API']; gh=os.environ['GITHUB_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']
    freeze_sha=os.environ['ATOMIC_FREEZE_COMMIT_SHA']
    expected_branch=os.environ.get('ATOMIC_SOURCE_BRANCH','rgi-ext-02g2g1-atomic-availability-execution-gate-20260820')
    if lock_exists(repo,gh):
        print('RGI_EXT_02G2G1_ALREADY_CONSUMED_STOP_NO_QUERY_NO_PROVIDER_REQUEST'); return 0
    EVIDENCE.mkdir(exist_ok=True)
    status,gpu,passed,errors=availability_query(key)
    state='RGI_EXT_02G2G_CARRIER_AVAILABLE' if passed else 'RGI_EXT_02G2G_CARRIER_UNAVAILABLE_NO_EXECUTION_AUTHORIZATION'
    receipt={'artifact_type':'RGI_EXT_02G2G1_AVAILABILITY_RECEIPT','experiment_id':'RGI-EXT-02G.2g.1','queried_at_ns':time.time_ns(),'http_status':status,'operation_type':'QUERY_ONLY_NO_MUTATION','gpu_type_id':GPU,'gpu_count':1,'secure_cloud':True,'state':state,'availability_passed':passed,'gpu_result':gpu,'query_errors':errors,'provider_create_request_sent':False,'pod_created':False,'scientific_measurement_started':False,'atomic_freeze_commit_sha':freeze_sha}
    receipt['receipt_sha256']=sha256_bytes(canon(receipt)); write_json(EVIDENCE/'AVAILABILITY_RECEIPT.json',receipt)
    if not passed:
        print(json.dumps({'state':state,'availability_passed':False,'receipt_sha256':receipt['receipt_sha256']},sort_keys=True)); return 0
    f=json.loads((ROOT/'rgi-ext-02g2g1'/'ATOMIC_AVAILABILITY_TO_EXECUTION_FREEZE.json').read_text())
    fields=[DOMAIN,receipt['receipt_sha256'],freeze_sha,f['frozen_scientific_lineage']['measurement_admissibility_sha256'],f['frozen_scientific_lineage']['carrier_equivalence_amendment_sha256'],f['frozen_scientific_lineage']['repair_freeze_head_sha'],f['frozen_scientific_lineage']['fresh_authorization_head_sha'],f['frozen_scientific_lineage']['fresh_measurement_identity']]
    identity_hash=hashlib.sha256('|'.join(fields).encode()).hexdigest(); execution_identity='RGI-EXT-02G.2g.1-EXEC-'+identity_hash[:24]
    age_seconds=(time.time_ns()-receipt['queried_at_ns'])/1e9
    if age_seconds>120: raise SystemExit('AVAILABILITY_RECEIPT_TOO_OLD_STOP_NO_PROVIDER_REQUEST')
    lock_payload={'ref':f'refs/heads/{LOCK_BRANCH}','sha':freeze_sha}
    code,obj=github_json('POST',f'/repos/{repo}/git/refs',gh,lock_payload)
    if code!=201:
        if code==422:
            print('RGI_EXT_02G2G1_LOCK_ALREADY_CONSUMED_STOP_NO_PROVIDER_REQUEST'); return 0
        raise SystemExit(f'LOCK_ACQUISITION_FAILED_HTTP_{code}_STOP_NO_PROVIDER_REQUEST')
    authorization={'artifact_type':'RGI_EXT_02G2G1_DETERMINISTIC_EXECUTION_AUTHORIZATION','experiment_id':'RGI-EXT-02G.2g.1','execution_identity':execution_identity,'identity_sha256':identity_hash,'availability_receipt_sha256':receipt['receipt_sha256'],'availability_state':state,'atomic_freeze_commit_sha':freeze_sha,'source_branch':expected_branch,'lock_ref':f'refs/heads/{LOCK_BRANCH}','lock_acquired':True,'lock_acquired_at_ns':time.time_ns(),'provider_create_requests_authorized':1,'provider_retry_authorized':False,'second_pod_substitution_authorized':False,'scientific_design_change':False,'pr10_data_reuse_authorized':False}
    authorization['authorization_sha256']=sha256_bytes(canon(authorization)); write_json(EVIDENCE/'EXECUTION_AUTHORIZATION.json',authorization)
    env=os.environ.copy(); env['TARGET_BRANCH']=expected_branch
    p=subprocess.run(['bash',str(ROOT/'rgi-ext-02g2a'/'runpod_equivalence_measurement_ci.sh')],cwd=ROOT,env=env)
    return p.returncode

if __name__=='__main__': raise SystemExit(main())

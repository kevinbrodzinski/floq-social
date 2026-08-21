#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path

GPU='NVIDIA RTX A4000'
QUERY='query { gpuTypes(input: { id: "NVIDIA RTX A4000" }) { id displayName lowestPrice(input: { gpuCount: 1, secureCloud: true }) { stockStatus uninterruptablePrice availableGpuCounts } } }'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':')).encode()

def main():
    key=os.environ['RUNPOD_API']
    url='https://api.runpod.io/graphql?'+urllib.parse.urlencode({'api_key':key})
    req=urllib.request.Request(url,data=json.dumps({'query':QUERY}).encode(),headers={'Content-Type':'application/json','User-Agent':'rgi-ext-02g2g-availability-gate/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(); status=r.status
    except urllib.error.HTTPError as e:
        raw=e.read(); status=e.code
    try: obj=json.loads(raw)
    except Exception: obj={'errors':[{'message':'NON_JSON_PROVIDER_RESPONSE'}]}
    rows=(obj.get('data') or {}).get('gpuTypes') or [] if isinstance(obj,dict) else []
    gpu=next((x for x in rows if x.get('id')==GPU),None)
    lp=(gpu or {}).get('lowestPrice') or {}
    stock=lp.get('stockStatus')
    counts=lp.get('availableGpuCounts') or []
    price=lp.get('uninterruptablePrice')
    query_ok=(200 <= status < 300 and not obj.get('errors')) if isinstance(obj,dict) else False
    passed=(query_ok and stock not in (None,'None') and 1 in counts and price is not None)
    if passed: state='RGI_EXT_02G2G_CARRIER_AVAILABLE'
    elif query_ok: state='RGI_EXT_02G2G_CARRIER_UNAVAILABLE_NO_EXECUTION_AUTHORIZATION'
    else: state='RGI_EXT_02G2G_AVAILABILITY_QUERY_ERROR_NO_EXECUTION_AUTHORIZATION'
    receipt={
      'artifact_type':'RGI_EXT_02G2G_CARRIER_AVAILABILITY_RECEIPT','experiment_id':'RGI-EXT-02G.2g',
      'queried_at_ns':time.time_ns(),'http_status':status,'operation_type':'QUERY_ONLY_NO_MUTATION',
      'gpu_type_id':GPU,'gpu_count':1,'secure_cloud':True,'state':state,'availability_passed':passed,
      'gpu_result':gpu,'provider_errors':obj.get('errors') if isinstance(obj,dict) else None,
      'provider_create_request_sent':False,'pod_created':False,'scientific_measurement_started':False
    }
    receipt['receipt_sha256']=hashlib.sha256(canon(receipt)).hexdigest()
    Path('evidence').mkdir(exist_ok=True)
    Path('evidence/AVAILABILITY_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'state':state,'availability_passed':passed,'gpu_result':gpu,'http_status':status,'receipt_sha256':receipt['receipt_sha256']},sort_keys=True))

if __name__=='__main__': main()

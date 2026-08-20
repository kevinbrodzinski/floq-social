#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

GPU='NVIDIA RTX A4000'
OUT=Path('evidence')

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def sha(o): return hashlib.sha256(canon(o)).hexdigest()

def gql(key,secure):
    q=f'''query {{ gpuTypes(input: {{ id: "{GPU}" }}) {{ id displayName lowestPrice(input: {{ gpuCount: 1, secureCloud: {str(secure).lower()} }}) {{ stockStatus uninterruptablePrice availableGpuCounts }} }} }}'''
    url='https://api.runpod.io/graphql?'+urllib.parse.urlencode({'api_key':key})
    req=urllib.request.Request(url,data=json.dumps({'query':q}).encode(),headers={'Content-Type':'application/json','User-Agent':'rgi-ext-02g2g2-readonly-audit/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(); status=r.status
    except urllib.error.HTTPError as e:
        raw=e.read(); status=e.code
    try: obj=json.loads(raw)
    except Exception: obj={'errors':[{'message':'NON_JSON_PROVIDER_RESPONSE'}]}
    rows=(obj.get('data') or {}).get('gpuTypes') or [] if isinstance(obj,dict) else []
    gpu=next((x for x in rows if x.get('id')==GPU),None)
    return {'http_status':status,'secureCloud_input':secure,'gpu_result':gpu,'errors':obj.get('errors') if isinstance(obj,dict) else None}

def load_json_cmd(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    try: data=json.loads(p.stdout) if p.stdout.strip() else None
    except Exception: data=None
    return {'returncode':p.returncode,'data':data,'stdout_tail':p.stdout[-2000:] if data is None else None,'stderr_tail':p.stderr[-2000:]}

def main():
    key=os.environ['RUNPOD_API']
    OUT.mkdir(exist_ok=True)
    secure=gql(key,True)
    nonsecure=gql(key,False)
    gpu_list=load_json_cmd([os.environ['RUNPODCTL'],'gpu','list','--include-unavailable'])
    dc_list=load_json_cmd([os.environ['RUNPODCTL'],'datacenter','list'])
    gpu_rows=gpu_list.get('data') or []
    cli_gpu=next((x for x in gpu_rows if x.get('gpuId')==GPU),None) if isinstance(gpu_rows,list) else None
    dcs=[]
    for dc in dc_list.get('data') or []:
        hits=[x for x in (dc.get('gpuAvailability') or []) if x.get('gpuId')==GPU]
        if hits:
            dcs.append({'id':dc.get('id'),'name':dc.get('name'),'location':dc.get('location'),'a4000':hits})
    receipt={
      'artifact_type':'RGI_EXT_02G2G2_READ_ONLY_AVAILABILITY_SEMANTICS_AUDIT',
      'experiment_id':'RGI-EXT-02G.2g.2',
      'queried_at_ns':time.time_ns(),
      'operations':['GraphQL gpuTypes/lowestPrice secureCloud=true','GraphQL gpuTypes/lowestPrice secureCloud=false','runpodctl gpu list --include-unavailable','runpodctl datacenter list'],
      'provider_create_request_sent':False,
      'pod_created':False,
      'scientific_measurement_started':False,
      'graphql_secure':secure,
      'graphql_secure_false':nonsecure,
      'runpodctl_gpu_a4000':cli_gpu,
      'runpodctl_gpu_command_returncode':gpu_list['returncode'],
      'runpodctl_gpu_stderr_tail':gpu_list['stderr_tail'],
      'runpodctl_datacenter_a4000':dcs,
      'runpodctl_datacenter_command_returncode':dc_list['returncode'],
      'runpodctl_datacenter_stderr_tail':dc_list['stderr_tail']
    }
    receipt['receipt_sha256']=sha(receipt)
    (OUT/'AVAILABILITY_SEMANTICS_AUDIT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__': main()

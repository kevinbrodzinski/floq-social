#!/usr/bin/env python3
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

STATE = Path(os.environ.get('RGI_EXT02G_STATE_DIR', '.rgi-ext-02g-state'))
STATE.mkdir(parents=True, exist_ok=True)


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)


def jprint(obj, code=0):
    print(json.dumps(obj, sort_keys=True))
    raise SystemExit(code)


def nvidia_query(fields):
    if not shutil.which('nvidia-smi'):
        return None, 'NVIDIA_SMI_NOT_FOUND'
    r = run(['nvidia-smi', f'--query-gpu={fields}', '--format=csv,noheader,nounits'])
    if r.returncode != 0:
        return None, 'NVIDIA_SMI_QUERY_FAILED'
    rows = [x.strip() for x in r.stdout.splitlines() if x.strip()]
    if not rows:
        return None, 'NO_GPU_ROWS'
    return rows, None


def identity():
    rows, err = nvidia_query('uuid,name,pci.bus_id,driver_version')
    if err:
        jprint({'status':'REFUSED','reason':err,'target_kind':'GPU_ENDPOINT','discrete_gpu':False}, 2)
    first = [x.strip() for x in rows[0].split(',')]
    if len(first) < 4:
        jprint({'status':'REFUSED','reason':'MALFORMED_NATIVE_IDENTITY','target_kind':'GPU_ENDPOINT','discrete_gpu':False}, 2)
    out = {
        'status':'PASS','target_kind':'DISCRETE_GPU','discrete_gpu':True,
        'vendor':'NVIDIA','device_uuid':first[0],'device_name':first[1],
        'pci_bus_id':first[2],'driver_version':first[3],
        'device_count':len(rows),'native_source':'nvidia-smi'
    }
    jprint(out)


def inventory():
    rows, err = nvidia_query('uuid,memory.total,memory.free,memory.used')
    if err:
        jprint({'status':'REFUSED','reason':err}, 2)
    vals = [x.strip() for x in rows[0].split(',')]
    if len(vals) < 4:
        jprint({'status':'REFUSED','reason':'MALFORMED_NATIVE_INVENTORY'}, 2)
    total_mib = int(float(vals[1])); free_mib = int(float(vals[2])); used_mib = int(float(vals[3]))
    jprint({
        'status':'PASS','device_uuid':vals[0],
        'primary_resource':'GPU_DEVICE_MEMORY', 'unit':'MiB',
        'capacity':total_mib,'free':free_mib,'used':used_mib,
        'native_source':'nvidia-smi'
    })


def quantum():
    # NVIDIA allocation granularity is API/context dependent. This adapter refuses
    # to invent a universal device-memory quantum from nvidia-smi alone.
    helper = os.environ.get('RGI_EXT02G_QUANTUM_HELPER')
    if not helper:
        jprint({'status':'REFUSED','reason':'NATIVE_QUANTUM_HELPER_NOT_CONFIGURED','native_source':'none'}, 3)
    r = run([helper])
    if r.returncode != 0:
        jprint({'status':'REFUSED','reason':'NATIVE_QUANTUM_HELPER_FAILED','stderr':r.stderr[-1000:]}, 3)
    try:
        obj = json.loads(r.stdout)
        q = float(obj['quantum'])
        if not (q > 0): raise ValueError('nonpositive')
    except Exception:
        jprint({'status':'REFUSED','reason':'INVALID_NATIVE_QUANTUM_RECEIPT'}, 3)
    obj['status'] = 'PASS'; jprint(obj)


def workload(level):
    helper = os.environ.get('RGI_EXT02G_WORKLOAD_HELPER')
    if not helper:
        jprint({'status':'REFUSED','reason':'GPU_WORKLOAD_HELPER_NOT_CONFIGURED'}, 4)
    r = run([helper, str(level)])
    if r.returncode != 0:
        jprint({'status':'REFUSED','reason':'GPU_WORKLOAD_FAILED','stderr':r.stderr[-2000:]}, 4)
    try: payload = json.loads(r.stdout)
    except Exception: jprint({'status':'REFUSED','reason':'INVALID_WORKLOAD_RECEIPT'},4)
    rid = hashlib.sha256((json.dumps(payload,sort_keys=True)+f'|{level}').encode()).hexdigest()
    receipt = {'status':'PASS','resource_level':level,'execution_receipt_id':rid,'payload':payload,'completed_at_ns':time.time_ns()}
    (STATE/'last_execution.json').write_text(json.dumps(receipt,sort_keys=True))
    jprint(receipt)


def response():
    p = STATE/'last_execution.json'
    if not p.exists(): jprint({'status':'REFUSED','reason':'NO_EXECUTION_RECEIPT'},5)
    helper = os.environ.get('RGI_EXT02G_RESPONSE_HELPER')
    if not helper: jprint({'status':'REFUSED','reason':'GPU_RESPONSE_HELPER_NOT_CONFIGURED'},5)
    e = json.loads(p.read_text())
    r = run([helper, e['execution_receipt_id']])
    if r.returncode != 0: jprint({'status':'REFUSED','reason':'GPU_RESPONSE_COLLECTION_FAILED','stderr':r.stderr[-2000:]},5)
    try: payload=json.loads(r.stdout)
    except Exception: jprint({'status':'REFUSED','reason':'INVALID_RESPONSE_RECEIPT'},5)
    out={'status':'PASS','execution_receipt_id':e['execution_receipt_id'],'response':payload,'collected_at_ns':time.time_ns()}
    (STATE/'last_response.json').write_text(json.dumps(out,sort_keys=True))
    jprint(out)


def seal():
    p=STATE/'last_response.json'
    if not p.exists(): jprint({'status':'REFUSED','reason':'NO_RESPONSE_RECEIPT'},6)
    raw=p.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    out={'status':'PASS','sealed_artifact':'last_response.json','sha256':sha,'bytes':len(raw),'sealed_at_ns':time.time_ns()}
    (STATE/'seal.json').write_text(json.dumps(out,sort_keys=True))
    jprint(out)

ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
for name in ['identity','resource-inventory','native-quantum','collect-response','seal-raw-outcome']: sub.add_parser(name)
w=sub.add_parser('run-workload'); w.add_argument('--resource-level',type=float,required=True)
a=ap.parse_args()
if a.cmd=='identity': identity()
elif a.cmd=='resource-inventory': inventory()
elif a.cmd=='native-quantum': quantum()
elif a.cmd=='run-workload': workload(a.resource_level)
elif a.cmd=='collect-response': response()
elif a.cmd=='seal-raw-outcome': seal()

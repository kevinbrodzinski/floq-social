#!/usr/bin/env python3
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path


def call(target, args, allow_refusal=False):
    r = subprocess.run([target] + args, text=True, capture_output=True)
    obj = None
    try:
        obj = json.loads(r.stdout.strip())
    except Exception:
        raise RuntimeError(f"non-JSON target output for {args[0]}: rc={r.returncode} stderr={r.stderr[-1000:]}")
    if r.returncode != 0 and not allow_refusal:
        raise RuntimeError(f"target refused {args[0]}: {obj}")
    return r.returncode, obj


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

ap=argparse.ArgumentParser()
ap.add_argument('--target', required=True, help='Executable implementing the six-command EXT-02G contract')
ap.add_argument('--out', default='RGI_EXT_02G_ADMISSION_RECEIPT.json')
ap.add_argument('--resource-level', type=float, default=0.25)
a=ap.parse_args()

started=time.time_ns()
rc, ident = call(a.target, ['identity'], allow_refusal=True)
receipt={
  'trial':'RGI-EXT-02G',
  'stage':'PLUGGABLE_REAL_GPU_EXECUTION_TARGET_ADMISSION',
  'target_executable':a.target,
  'started_at_ns':started,
  'identity':ident,
  'theta_estimated':False,
  'brodzinski_class_assigned':False,
  'brodzinski_state_certified':False,
  'claim_boundary':'Execution-carrier admission only. No alpha, beta, Theta, class, or certification is produced here.'
}

if rc != 0 or ident.get('status') != 'PASS' or ident.get('target_kind') != 'DISCRETE_GPU' or ident.get('discrete_gpu') is not True:
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':ident.get('reason','IDENTITY_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

rc, inv=call(a.target,['resource-inventory'],allow_refusal=True); receipt['resource_inventory']=inv
if rc != 0 or inv.get('status')!='PASS' or not inv.get('primary_resource') or float(inv.get('capacity',0))<=0:
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':inv.get('reason','RESOURCE_INVENTORY_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

rc,q=call(a.target,['native-quantum'],allow_refusal=True); receipt['native_quantum']=q
if rc != 0 or q.get('status')!='PASS' or float(q.get('quantum',0))<=0:
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':q.get('reason','NATIVE_QUANTUM_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

rc,w=call(a.target,['run-workload','--resource-level',str(a.resource_level)],allow_refusal=True); receipt['workload']=w
if rc != 0 or w.get('status')!='PASS' or not w.get('execution_receipt_id'):
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':w.get('reason','WORKLOAD_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

rc,response=call(a.target,['collect-response'],allow_refusal=True); receipt['response']=response
if rc != 0 or response.get('status')!='PASS' or response.get('execution_receipt_id')!=w.get('execution_receipt_id'):
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':response.get('reason','RESPONSE_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

rc,seal=call(a.target,['seal-raw-outcome'],allow_refusal=True); receipt['seal']=seal
if rc != 0 or seal.get('status')!='PASS' or len(seal.get('sha256',''))!=64:
    receipt.update({'result':'GPU_TARGET_INELIGIBLE','terminal_reason':seal.get('reason','SEAL_GATE_FAILED')})
    write(a.out,receipt); print(json.dumps(receipt,sort_keys=True)); raise SystemExit(0)

receipt.update({
 'result':'GPU_EXECUTION_CARRIER_ADMITTED',
 'terminal_reason':None,
 'carrier_commitment_sha256':hashlib.sha256(json.dumps({'identity':ident,'inventory':inv,'quantum':q,'workload':w,'response':response,'seal':seal},sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'completed_at_ns':time.time_ns()
})
write(a.out,receipt); print(json.dumps(receipt,sort_keys=True))

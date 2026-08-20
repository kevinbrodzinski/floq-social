#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=Path(__file__).with_name('CARRIER_EQUIVALENCE_AMENDMENT.json')
M=Path(__file__).with_name('FREEZE_MANIFEST_SHA256.json')
F=ROOT/'rgi-ext-02g2'/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
sys.path.insert(0,str(ROOT/'rgi-ext-02g2'))
from gpu_measurement_common import identity, quantum, idle_gate

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p:Path,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def ver(v:str):
    out=[]
    for x in v.split('.'):
        s=''.join(c for c in x if c.isdigit())
        out.append(int(s or 0))
    return tuple((out+[0,0,0])[:3])
def smi_count():
    p=subprocess.run(['nvidia-smi','--query-gpu=uuid','--format=csv,noheader'],text=True,capture_output=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    return len([x for x in p.stdout.splitlines() if x.strip()])
def mig_state():
    p=subprocess.run(['nvidia-smi','-q'],text=True,capture_output=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    vals=[]; inside=False
    for line in p.stdout.splitlines():
        s=line.strip()
        if s=='MIG Mode':inside=True;continue
        if inside and s.startswith('Current') and ':' in s:vals.append(s.split(':',1)[1].strip());inside=False
    return vals or ['N/A']
def torch_probe():
    code='''import json,torch\nassert torch.cuda.is_available()\ntorch.cuda.set_device(0)\np=torch.cuda.get_device_properties(0)\nn=1024\na=torch.arange(n*n,dtype=torch.float32,device="cuda").reshape(n,n)\nb=torch.full((n,n),1.0/n,dtype=torch.float32,device="cuda")\nc=a@b\ntorch.cuda.synchronize()\nprint(json.dumps({"device_name":str(p.name),"compute_capability":[int(p.major),int(p.minor)],"native_capacity_bytes":int(p.total_memory),"torch_version":torch.__version__,"torch_cuda":torch.version.cuda,"checksum":float(c[0,0].item()+c[-1,-1].item())},sort_keys=True))'''
    p=subprocess.run([sys.executable,'-c',code],text=True,capture_output=True,timeout=90)
    if p.returncode:raise RuntimeError('torch probe failed: '+p.stderr[-1500:])
    return json.loads(p.stdout.strip().splitlines()[-1])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True);started=time.time_ns()
    a=json.loads(A.read_text());m=json.loads(M.read_text());f=json.loads(F.read_text());req=a['carrier_equivalence_class']['requirements'];checks={};obs={}
    checks['frozen_amendment_hash']=sha(A)==m['files']['CARRIER_EQUIVALENCE_AMENDMENT.json']=='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'
    checks['frozen_parent_measurement_hash']=sha(F)=='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
    ident=identity();obs['identity']=ident; checks['device_name']=ident['device_name']==req['device_name_exact']; checks['driver_range']=ver(ident['driver_version'])>=ver(req['nvidia_driver_rule']['minimum_inclusive']) and ver(ident['driver_version'])<ver(req['nvidia_driver_rule']['maximum_exclusive'])
    obs['gpu_count']=smi_count();checks['gpu_count']=obs['gpu_count']==req['gpu_count_exact']
    obs['mig_mode']=mig_state();checks['no_mig_partitioning']=all(x in {'Disabled','N/A','[N/A]'} for x in obs['mig_mode'])
    q=quantum();obs['native_quantum']=q;checks['native_quantum']=int(q['quantum'])==req['native_quantum_bytes_exact']
    tp=torch_probe();obs['torch_probe']=tp;checks['compute_capability']=tp['compute_capability']==req['compute_capability_exact'];checks['native_capacity_bytes']=int(tp['native_capacity_bytes'])==req['native_capacity_bytes_exact'];checks['nvidia_smi_capacity_mib']=abs(float(ident['memory_total_mib_nvidia_smi'])-float(req['nvidia_smi_capacity_mib_exact']))<0.5;checks['torch_cuda_family']=str(tp['torch_cuda']).startswith(req['cuda_runtime_family']);checks['compatibility_checksum']=abs(float(tp['checksum'])-float(req['compatibility_probe_checksum_reference']))<=float(req['workload_checksum_abs_tolerance'])
    try:cv=importlib.metadata.version('cuda-python')
    except Exception:cv='UNAVAILABLE'
    obs['cuda_python_version']=cv;checks['cuda_python_version']=cv==req['cuda_python_exact']
    ok_env,env=idle_gate(f);obs['idle_environment_gate']=env;checks['unchanged_idle_environment_gate']=ok_env
    passed=all(checks.values());state=a['preflight_protocol']['pass_state'] if passed else a['preflight_protocol']['failure_state']
    cert={'artifact_type':'RGI_EXT_02G2A_CARRIER_EQUIVALENCE_CERTIFICATE','experiment_id':'RGI-EXT-02G.2a','state':state,'carrier_class_id':a['carrier_equivalence_class']['class_id'],'physical_uuid_role':a['carrier_equivalence_class']['physical_uuid_role'],'observed':obs,'checks':checks,'all_checks_passed':passed,'amendment_sha256':sha(A),'parent_measurement_freeze_sha256':sha(F),'scientific_measurement_started':False,'started_at_ns':started,'completed_at_ns':time.time_ns()}
    cert['certificate_sha256']=hashlib.sha256(json.dumps(cert,sort_keys=True,separators=(',',':')).encode()).hexdigest();dump(out/'EQUIVALENCE_CERTIFICATE.json',cert)
    if not passed:
        term={'artifact_type':'RGI_EXT_02G2A_TERMINAL_RECEIPT','terminal_state':'GPU_CARRIER_EQUIVALENCE_REFUSED_STOP_NO_MEASUREMENT','stage':'CARRIER_EQUIVALENCE_PREFLIGHT','equivalence_certificate_sha256':cert['certificate_sha256'],'scientific_measurement_started':False,'completed_at_ns':time.time_ns(),'evidence':cert};term['receipt_sha256']=hashlib.sha256(json.dumps(term,sort_keys=True,separators=(',',':')).encode()).hexdigest();dump(out/'TERMINAL_RECEIPT.json',term)
    print(state);return 0
if __name__=='__main__':raise SystemExit(main())

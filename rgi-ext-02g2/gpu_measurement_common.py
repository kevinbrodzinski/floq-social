#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, time
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
FREEZE=HERE/'MEASUREMENT_ADMISSIBILITY_FREEZE.json'
MANIFEST=HERE/'FREEZE_MANIFEST_SHA256.json'
FREEZE_SHA='aa7c9954b21e55943ae6683519ea41fc387b03d46cab9b2aa79570222ca643d2'
ALLOWED_TERMINALS={
 'GPU_IDENTITY_MISMATCH_STOP_NO_MEASUREMENT','NATIVE_QUANTUM_MISMATCH_STOP_NO_MEASUREMENT',
 'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','ALPHA_UNIDENTIFIABLE_STOP_NO_THETA',
 'BETA_GEOMETRY_PROFILE_INAPPLICABLE_STOP_NO_THETA','AMBIGUOUS_STOP_BEFORE_BLIND_OUTCOME',
 'PREDICTION_LOCKED_HOLDOUT_UNOPENED'}

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def canon(o:Any)->bytes:return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def dump(path:Path,o:Any):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def run(cmd:list[str],timeout=30)->str:
 p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
 if p.returncode: raise RuntimeError(f'{cmd!r}: {p.stderr[-2000:]}')
 return p.stdout.strip()

def load_freeze()->dict[str,Any]:
 if sha(FREEZE)!=FREEZE_SHA: raise RuntimeError('frozen measurement contract hash mismatch')
 m=json.loads(MANIFEST.read_text())
 if m['files']['MEASUREMENT_ADMISSIBILITY_FREEZE.json']!=FREEZE_SHA: raise RuntimeError('manifest/freeze mismatch')
 f=json.loads(FREEZE.read_text())
 if f['authorized_next_state']!='FROZEN_STOP_BEFORE_SCIENTIFIC_GPU_MEASUREMENT' or f['custody']['scientific_sweep_executed'] is not False:
  raise RuntimeError('freeze is not the prospective pre-measurement state')
 return f

def identity()->dict[str,Any]:
 row=run(['nvidia-smi','--query-gpu=uuid,name,pci.bus_id,driver_version,memory.total','--format=csv,noheader,nounits']).splitlines()[0]
 p=[x.strip() for x in row.split(',')]
 if len(p)!=5: raise RuntimeError('unexpected identity row '+row)
 return {'device_uuid':p[0],'device_name':p[1],'pci_bus_id':p[2],'driver_version':p[3],'memory_total_mib_nvidia_smi':float(p[4])}

def slowdown()->tuple[bool,list[str]]:
 lines=[];active=False
 for line in run(['nvidia-smi','-q','-d','PERFORMANCE']).splitlines():
  s=line.strip()
  if 'SW Thermal Slowdown' in s or 'HW Thermal Slowdown' in s:
   lines.append(s)
   if ':' in s and s.split(':',1)[1].strip()=='Active':active=True
 return active,lines

def compute_processes()->list[dict[str,str]]:
 p=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'],text=True,capture_output=True,timeout=20)
 if p.returncode: raise RuntimeError('compute-app query failed '+p.stderr[-1000:])
 out=[]
 for line in p.stdout.splitlines():
  a=[x.strip() for x in line.split(',',1)]
  if a and a[0].isdigit():out.append({'pid':a[0],'process_name':a[1] if len(a)>1 else ''})
 return out

def snapshot()->dict[str,Any]:
 row=run(['nvidia-smi','--query-gpu=temperature.gpu,utilization.gpu,memory.used,pstate,power.draw','--format=csv,noheader,nounits']).splitlines()[0]
 p=[x.strip() for x in row.split(',')]
 if len(p)!=5: raise RuntimeError('unexpected snapshot row '+row)
 active,ev=slowdown()
 return {'temperature_c':float(p[0]),'utilization_pct':float(p[1]),'memory_used_mib':float(p[2]),'pstate':p[3],
  'power_draw_w':None if p[4] in {'N/A','[N/A]'} else float(p[4]),'thermal_or_hw_slowdown_active':active,
  'slowdown_evidence':ev,'compute_processes':compute_processes(),'sampled_at_ns':time.time_ns()}

def idle_gate(f:dict[str,Any])->tuple[bool,dict[str,Any]]:
 g=f['thermal_load_exclusions'];samples=[];v=[];n=int(g['pre_point_idle_samples']);period=float(g['idle_sample_period_seconds'])
 for i in range(n):
  s=snapshot();samples.append(s)
  if i+1<n:time.sleep(period)
 for i,s in enumerate(samples):
  if s['utilization_pct']>float(g['max_gpu_utilization_pct_each_idle_sample']):v.append(f'{i}:utilization')
  if s['memory_used_mib']>float(g['max_pre_point_device_memory_used_mib']):v.append(f'{i}:memory')
  if s['temperature_c']>float(g['max_pre_point_temperature_c']):v.append(f'{i}:temperature')
  if s['thermal_or_hw_slowdown_active'] and not g['active_thermal_or_hw_slowdown_allowed']:v.append(f'{i}:thermal_slowdown')
  if len(s['compute_processes'])>int(g['external_compute_processes_allowed']):v.append(f'{i}:external_compute')
 return not v,{'samples':samples,'violations':v}

def quantum()->dict[str,Any]:
 h=HERE.parent/'rgi-ext-02g'/'runpod_quantum_helper.py'
 p=subprocess.run(['python3',str(h)],text=True,capture_output=True,timeout=30)
 try:o=json.loads(p.stdout.strip())
 except Exception as e:raise RuntimeError('quantum helper non-json') from e
 if p.returncode or o.get('status')!='PASS':raise RuntimeError('quantum helper failed '+repr(o))
 return o

def terminal(out:Path,state:str,stage:str,evidence:Any,started:int)->dict[str,Any]:
 if state not in ALLOWED_TERMINALS:raise RuntimeError('unregistered terminal '+state)
 o={'artifact_type':'RGI_EXT_02G2_PRIMARY_MEASUREMENT_TERMINAL_RECEIPT','experiment_id':'RGI-EXT-02G.2','terminal_state':state,
  'stage':stage,'started_at_ns':started,'completed_at_ns':time.time_ns(),'freeze_sha256':FREEZE_SHA,'blind_holdout_collected':False,
  'boundary_contact_H_seen':False,'boundary_contact_K_seen':False,'evidence':evidence}
 o['receipt_sha256']=hashlib.sha256(canon(o)).hexdigest();dump(out/'TERMINAL_RECEIPT.json',o);return o

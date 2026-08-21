#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, time
from pathlib import Path

def smi_snapshot():
    q=['nvidia-smi','--query-gpu=uuid,name,temperature.gpu,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits']
    p=subprocess.run(q,text=True,capture_output=True,timeout=20)
    if p.returncode: raise RuntimeError(p.stderr[-1000:])
    a=[x.strip() for x in p.stdout.strip().splitlines()[0].split(',')]
    return {'uuid':a[0],'name':a[1],'temperature_c':float(a[2]),'utilization_pct':float(a[3]),'memory_used_mib':float(a[4]),'memory_total_mib':float(a[5]),'at_ns':time.time_ns()}

def med(xs):
    y=sorted(float(x) for x in xs); n=len(y)
    return y[n//2] if n%2 else (y[n//2-1]+y[n//2])/2

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--p',type=float,required=True);ap.add_argument('--quantum',type=int,required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out)
    import torch
    if not torch.cuda.is_available(): raise SystemExit('CUDA_RUNTIME_GPU_UNAVAILABLE')
    torch.cuda.set_device(0); props=torch.cuda.get_device_properties(0); total=int(props.total_memory)
    requested_unaligned=int(math.floor(a.p*total)); requested=(requested_unaligned//a.quantum)*a.quantum
    if requested < a.quantum: requested=a.quantum
    torch.manual_seed(260819); torch.cuda.manual_seed_all(260819)
    A=torch.randn((1024,1024),device='cuda',dtype=torch.float32)
    B=torch.randn((1024,1024),device='cuda',dtype=torch.float32)
    torch.cuda.synchronize()
    def matmul_ms():
        vals=[]
        for _ in range(2): C=A@B; torch.cuda.synchronize()
        for _ in range(5):
            s=torch.cuda.Event(enable_timing=True);e=torch.cuda.Event(enable_timing=True);s.record();C=A@B;e.record();torch.cuda.synchronize();vals.append(float(s.elapsed_time(e)))
        chk=float(C[0,0].item()+C[-1,-1].item())
        return vals,chk
    pre=smi_snapshot(); base,chk1=matmul_ms(); baseline_temp=smi_snapshot()
    buf=torch.empty(requested,dtype=torch.uint8,device='cuda');buf.fill_(0x5A);torch.cuda.synchronize();time.sleep(2.0)
    pressure_pre=smi_snapshot(); press,chk2=matmul_ms(); pressure_post=smi_snapshot()
    touched=int(buf[0].item())+int(buf[-1].item())
    obj={'status':'PASS','requested_p':a.p,'native_capacity_bytes':total,'native_quantum_bytes':a.quantum,'requested_bytes_unaligned':requested_unaligned,'requested_bytes_aligned':requested,'realized_p':requested/total,'baseline_cuda_ms':base,'pressure_cuda_ms':press,'baseline_median_ms':med(base),'pressure_median_ms':med(press),'D':med(press)/med(base)-1.0,'compute_checksum_baseline':chk1,'compute_checksum_pressure':chk2,'memory_touch_checksum':touched,'pre_snapshot':pre,'baseline_snapshot':baseline_temp,'pressure_pre_snapshot':pressure_pre,'pressure_post_snapshot':pressure_post,'temperature_rise_c':pressure_post['temperature_c']-baseline_temp['temperature_c'],'device_name':str(props.name),'completed_at_ns':time.time_ns()}
    obj['payload_sha256']=hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    out.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); print(json.dumps(obj,sort_keys=True))
if __name__=='__main__':main()

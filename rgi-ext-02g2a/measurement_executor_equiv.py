#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'rgi-ext-02g2'))
from gpu_measurement_common import load_freeze, identity, quantum, idle_gate, terminal, dump, FREEZE_SHA
from measurement_executor import fit_alpha, classify
AMEND=ROOT/'rgi-ext-02g2a'/'CARRIER_EQUIVALENCE_AMENDMENT.json'
AMEND_SHA='04716f93f260ed3ef8e23201ef21775a25ad2c2cd40949e09a93a99d21472ba0'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--certificate',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);started=time.time_ns();f=load_freeze()
    if hashlib.sha256(AMEND.read_bytes()).hexdigest()!=AMEND_SHA:raise SystemExit('AMENDMENT_HASH_MISMATCH')
    cert=json.loads(Path(a.certificate).read_text())
    if cert.get('state')!='CARRIER_EQUIVALENCE_CERTIFIED' or cert.get('all_checks_passed') is not True or cert.get('amendment_sha256')!=AMEND_SHA or cert.get('scientific_measurement_started') is not False:raise SystemExit('VALID_EQUIVALENCE_CERTIFICATE_REQUIRED')
    ident=identity();dump(out/'GPU_IDENTITY.json',ident)
    observed=cert['observed']['identity']
    if ident['device_uuid']!=observed['device_uuid'] or ident['device_name']!=observed['device_name']:raise SystemExit('CERTIFICATE_CARRIER_CHANGED')
    q=quantum();dump(out/'NATIVE_QUANTUM.json',q)
    if int(q['quantum'])!=int(f['native_quantum']['bytes']):
        terminal(out,'NATIVE_QUANTUM_MISMATCH_STOP_NO_MEASUREMENT','NATIVE_QUANTUM_PREFLIGHT',{'observed':q,'required':f['native_quantum'],'equivalence_certificate':cert},started);return 0
    retained=[];point_counter=0;worker=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'
    for blk in f['measurement_ordering']['blocks']:
        b={'block':blk['block'],'kind':blk['kind'],'points':{}}
        for idx in blk['level_indices']:
            ok,gate=idle_gate(f);dump(out/f'preflight_block_{blk["block"]:02d}_level_{idx:02d}.json',gate)
            if not ok:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','PRE_POINT_ENVIRONMENT_GATE',{'block':blk['block'],'level_index':idx,'gate':gate,'equivalence_certificate_sha256':cert['certificate_sha256']},started);return 0
            p=float(f['alpha_measurement_grid']['requested_p'][idx]);pf=out/f'point_block_{blk["block"]:02d}_level_{idx:02d}.json'
            pr=subprocess.run([sys.executable,str(worker),'--p',repr(p),'--quantum',str(q['quantum']),'--out',str(pf)],text=True,capture_output=True)
            if pr.returncode!=0:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','POINT_EXECUTION_FAILURE',{'block':blk['block'],'level_index':idx,'stderr':pr.stderr[-2000:]},started);return 0
            obj=json.loads(pf.read_text());g=f['thermal_load_exclusions'];violations=[]
            if obj['pressure_pre_snapshot']['temperature_c']>float(g['max_pressure_phase_temperature_c']) or obj['pressure_post_snapshot']['temperature_c']>float(g['max_pressure_phase_temperature_c']):violations.append('pressure_temperature')
            if obj['temperature_rise_c']>float(g['post_pressure_max_temperature_rise_from_baseline_c']):violations.append('temperature_rise')
            if obj['pressure_pre_snapshot']['thermal_or_hw_slowdown_active'] or obj['pressure_post_snapshot']['thermal_or_hw_slowdown_active']:violations.append('thermal_or_hw_slowdown')
            if violations:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','PRESSURE_ENVIRONMENT_GATE',{'block':blk['block'],'level_index':idx,'violations':violations,'point':obj},started);return 0
            b['points'][str(idx)]=obj;point_counter+=1
        dump(out/f'block_{blk["block"]:02d}.json',b)
        if blk['kind']=='RETAINED':retained.append(b['points'])
    alpha,err=fit_alpha(retained,f)
    if err is not None:
        dump(out/'ALPHA_FAILURE.json',err);terminal(out,'ALPHA_UNIDENTIFIABLE_STOP_NO_THETA','ALPHA_ESTIMATOR',err,started);return 0
    dump(out/'ALPHA_ESTIMATE.json',alpha)
    if not alpha['passed']:
        terminal(out,'ALPHA_UNIDENTIFIABLE_STOP_NO_THETA','ALPHA_ESTIMATOR_GATES',alpha,started);return 0
    beta=f['beta_estimator'];req=beta['certificate_requirements'];beta_ok=(req['chart_dimension']==1 and req['boundary_manifold']=='single upper endpoint p=1' and req['coordinate_linear_in_native_bytes'] and req['normal_codimension_c']==1 and req['normal_flatness_order_m']==1)
    if not beta_ok:
        terminal(out,'BETA_GEOMETRY_PROFILE_INAPPLICABLE_STOP_NO_THETA','BETA_CERTIFICATE',beta,started);return 0
    beta_hat=float(beta['beta_hat']);theta=alpha['alpha_hat']+beta_hat;theta_ci=[alpha['ci95'][0]+beta_hat,alpha['ci95'][1]+beta_hat];cl=classify(theta,theta_ci)
    seal={'artifact_type':'RGI_EXT_02G2A_PREDICTION_SEAL','freeze_sha256':FREEZE_SHA,'amendment_sha256':AMEND_SHA,'equivalence_certificate_sha256':cert['certificate_sha256'],'carrier_uuid_provenance':ident['device_uuid'],'alpha':alpha,'beta_hat':beta_hat,'beta_kind':beta['kind'],'theta_hat':theta,'theta_ci95':theta_ci,'class':cl,'blind_holdout_collected':False,'boundary_contact_H_seen':False,'boundary_contact_K_seen':False,'measurement_points_executed':point_counter,'sealed_at_ns':time.time_ns()}
    seal['seal_sha256']=hashlib.sha256(json.dumps(seal,sort_keys=True,separators=(',',':')).encode()).hexdigest();dump(out/'PREDICTION_SEAL.json',seal)
    if cl=='AMBIGUOUS':terminal(out,'AMBIGUOUS_STOP_BEFORE_BLIND_OUTCOME','CLASSIFICATION',seal,started);return 0
    terminal(out,'PREDICTION_LOCKED_HOLDOUT_UNOPENED','PREDICTION_SEAL',seal,started);return 0
if __name__=='__main__':raise SystemExit(main())

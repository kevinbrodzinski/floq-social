#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, random, statistics, subprocess, sys, time
from pathlib import Path
from gpu_measurement_common import load_freeze, identity, quantum, idle_gate, terminal, dump, FREEZE_SHA

def linfit(xs,ys):
    n=len(xs); xm=sum(xs)/n; ym=sum(ys)/n; sxx=sum((x-xm)**2 for x in xs)
    if sxx<=0: raise ValueError('degenerate x')
    slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/sxx; intercept=ym-slope*xm
    pred=[intercept+slope*x for x in xs]; ssr=sum((y-p)**2 for y,p in zip(ys,pred)); sst=sum((y-ym)**2 for y in ys)
    return slope,intercept,1.0-ssr/sst if sst>0 else 1.0

def percentile(v,q):
    s=sorted(v); pos=(len(s)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return s[lo]
    return s[lo]*(hi-pos)+s[hi]*(pos-lo)

def aggregate(blocks,levels):
    out=[]
    for idx in range(levels):
        vals=[float(b[str(idx)]['D']) for b in blocks]
        ps=[float(b[str(idx)]['realized_p']) for b in blocks]
        out.append({'level_index':idx,'realized_p':statistics.median(ps),'U':statistics.median(vals),'block_D':vals})
    return out

def fit_alpha(blocks,freeze):
    levels=len(freeze['alpha_measurement_grid']['requested_p']); agg=aggregate(blocks,levels)
    if not all(x['U']>0 for x in agg): return None,{'reason':'NONPOSITIVE_AGGREGATED_U','aggregated':agg}
    xs=[math.log(x['realized_p']) for x in agg]; ys=[math.log(x['U']) for x in agg]; a,b,r2=linfit(xs,ys)
    loo=[]
    for j in range(levels):
        xx=[x for i,x in enumerate(xs) if i!=j]; yy=[y for i,y in enumerate(ys) if i!=j]; loo.append(linfit(xx,yy)[0])
    rng=random.Random(260819); boot=[]
    for _ in range(10000):
        sample=[blocks[rng.randrange(len(blocks))] for __ in range(len(blocks))]
        ag=aggregate(sample,levels)
        if all(x['U']>0 for x in ag): boot.append(linfit([math.log(x['realized_p']) for x in ag],[math.log(x['U']) for x in ag])[0])
    if len(boot)!=10000:return None,{'reason':'BOOTSTRAP_POSITIVITY_COLLAPSE','valid_bootstrap':len(boot),'required_bootstrap':10000,'aggregated':agg}
    lo,hi=percentile(boot,.025),percentile(boot,.975)
    res={'alpha_hat':a,'logA_hat':b,'r2':r2,'ci95':[lo,hi],'ci_width':hi-lo,'loo_alpha_min':min(loo),'loo_alpha_max':max(loo),'loo_alpha_range':max(loo)-min(loo),'bootstrap_valid_draws':len(boot),'aggregated':agg}
    g=freeze['alpha_estimator']['gates']
    checks={'all_15_levels_required':len(agg)==15,'alpha_ci_low_strictly_gt':lo>0,'alpha_ci_width_max':(hi-lo)<=float(g['alpha_ci_width_max']),'leave_one_level_out_alpha_range_max':(max(loo)-min(loo))<=float(g['leave_one_level_out_alpha_range_max']),'r2_min':r2>=float(g['r2_min'])}
    res['gate_checks']=checks;res['passed']=all(checks.values());return res,None

def classify(theta,ci):
    lo,hi=ci
    if lo>1.03:return 'QUADRATIC'
    if hi<0.97:return 'SUPERQUADRATIC'
    if abs(theta-1)<=0.03 and lo>=0.94 and hi<=1.06:return 'MARGINAL'
    return 'AMBIGUOUS'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);started=time.time_ns();f=load_freeze()
    ident=identity();dump(out/'GPU_IDENTITY.json',ident); lock=f['gpu_identity_lock']
    if ident['device_uuid']!=lock['device_uuid'] or ident['device_name']!=lock['device_name']:
        terminal(out,'GPU_IDENTITY_MISMATCH_STOP_NO_MEASUREMENT','GPU_IDENTITY_PREFLIGHT',{'observed':ident,'required':lock},started);return 0
    q=quantum();dump(out/'NATIVE_QUANTUM.json',q)
    if int(q['quantum'])!=int(f['native_quantum']['bytes']):
        terminal(out,'NATIVE_QUANTUM_MISMATCH_STOP_NO_MEASUREMENT','NATIVE_QUANTUM_PREFLIGHT',{'observed':q,'required':f['native_quantum']},started);return 0
    retained=[]; point_counter=0; worker=Path(__file__).with_name('gpu_measurement_point.py')
    for blk in f['measurement_ordering']['blocks']:
        b={'block':blk['block'],'kind':blk['kind'],'points':{}}
        for idx in blk['level_indices']:
            ok,gate=idle_gate(f); dump(out/f'preflight_block_{blk["block"]:02d}_level_{idx:02d}.json',gate)
            if not ok:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','PRE_POINT_ENVIRONMENT_GATE',{'block':blk['block'],'level_index':idx,'gate':gate},started);return 0
            p=float(f['alpha_measurement_grid']['requested_p'][idx]); pf=out/f'point_block_{blk["block"]:02d}_level_{idx:02d}.json'
            pr=subprocess.run([sys.executable,str(worker),'--p',repr(p),'--quantum',str(q['quantum']),'--out',str(pf)],text=True,capture_output=True)
            if pr.returncode!=0:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','POINT_EXECUTION_FAILURE',{'block':blk['block'],'level_index':idx,'stderr':pr.stderr[-2000:]},started);return 0
            obj=json.loads(pf.read_text()); g=f['thermal_load_exclusions']; violations=[]
            if obj['pressure_pre_snapshot']['temperature_c']>float(g['max_pressure_phase_temperature_c']) or obj['pressure_post_snapshot']['temperature_c']>float(g['max_pressure_phase_temperature_c']):violations.append('pressure_temperature')
            if obj['temperature_rise_c']>float(g['post_pressure_max_temperature_rise_from_baseline_c']):violations.append('temperature_rise')
            if obj['pressure_pre_snapshot']['thermal_or_hw_slowdown_active'] or obj['pressure_post_snapshot']['thermal_or_hw_slowdown_active']:violations.append('thermal_or_hw_slowdown')
            if violations:
                terminal(out,'ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE','PRESSURE_ENVIRONMENT_GATE',{'block':blk['block'],'level_index':idx,'violations':violations,'point':obj},started);return 0
            b['points'][str(idx)]=obj; point_counter+=1
        dump(out/f'block_{blk["block"]:02d}.json',b)
        if blk['kind']=='RETAINED':retained.append(b['points'])
    alpha,err=fit_alpha(retained,f)
    if err is not None:
        dump(out/'ALPHA_FAILURE.json',err);terminal(out,'ALPHA_UNIDENTIFIABLE_STOP_NO_THETA','ALPHA_ESTIMATOR',err,started);return 0
    dump(out/'ALPHA_ESTIMATE.json',alpha)
    if not alpha['passed']:
        terminal(out,'ALPHA_UNIDENTIFIABLE_STOP_NO_THETA','ALPHA_ESTIMATOR_GATES',alpha,started);return 0
    beta=f['beta_estimator']; req=beta['certificate_requirements']
    beta_ok=(req['chart_dimension']==1 and req['boundary_manifold']=='single upper endpoint p=1' and req['coordinate_linear_in_native_bytes'] and req['normal_codimension_c']==1 and req['normal_flatness_order_m']==1)
    if not beta_ok:
        terminal(out,'BETA_GEOMETRY_PROFILE_INAPPLICABLE_STOP_NO_THETA','BETA_CERTIFICATE',beta,started);return 0
    beta_hat=float(beta['beta_hat']);theta=alpha['alpha_hat']+beta_hat; theta_ci=[alpha['ci95'][0]+beta_hat,alpha['ci95'][1]+beta_hat];cl=classify(theta,theta_ci)
    seal={'artifact_type':'RGI_EXT_02G2_PREDICTION_SEAL','freeze_sha256':FREEZE_SHA,'alpha':alpha,'beta_hat':beta_hat,'beta_kind':beta['kind'],'theta_hat':theta,'theta_ci95':theta_ci,'class':cl,'blind_holdout_collected':False,'boundary_contact_H_seen':False,'boundary_contact_K_seen':False,'measurement_points_executed':point_counter,'sealed_at_ns':time.time_ns()}
    seal['seal_sha256']=hashlib.sha256(json.dumps(seal,sort_keys=True,separators=(',',':')).encode()).hexdigest();dump(out/'PREDICTION_SEAL.json',seal)
    if cl=='AMBIGUOUS':terminal(out,'AMBIGUOUS_STOP_BEFORE_BLIND_OUTCOME','CLASSIFICATION',seal,started);return 0
    terminal(out,'PREDICTION_LOCKED_HOLDOUT_UNOPENED','PREDICTION_SEAL',seal,started);return 0
if __name__=='__main__':raise SystemExit(main())

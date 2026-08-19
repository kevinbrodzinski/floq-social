#!/usr/bin/env python3
import argparse,json,hashlib,urllib.request
from pathlib import Path

def get(u):
    with urllib.request.urlopen(u,timeout=5) as r: return json.load(r)

a=argparse.ArgumentParser();a.add_argument('--base',required=True);a.add_argument('--subject',required=True);a.add_argument('--profile',required=True);a.add_argument('--arch',required=True);a.add_argument('--out',required=True);z=a.parse_args()
pb=Path(z.profile).read_bytes();p=json.loads(pb);ph=hashlib.sha256(pb).hexdigest();checks=[]
c=get(z.base+'/rgi/v1/capabilities')
checks += [('rgi-version',c.get('rgi_version')=='1.0.0'),('bs-compat',c.get('bs_core_compatibility')=='BS-CORE-1.0-COMPAT'),('profile-sha',c.get('benchmark_profiles',[{}])[0].get('sha256')==ph)]
rp=get(z.base+f"/rgi/v1/benchmark-profiles/{p['profile_id']}/{p['version']}");checks.append(('profile-exact',rp==p))
s=get(z.base+'/rgi/v1/states/'+z.subject);ext=s.get('extensions',{}).get('org.resourcegeometry.ext02a',{})
checks += [
 ('status-unknown',s.get('status')=='UNKNOWN'),
 ('no-brodzinski','brodzinski' not in s),
 ('reason',s.get('reason',{}).get('code')=='MEASUREMENT_NOT_EXECUTED'),
 ('resource',s.get('resources',{}).get('primary',{}).get('id')=='bs.compute.cpu.capacity'),
 ('method',s.get('measurement',{}).get('method_id')=='bs.method.source_audit.v0.1'),
 ('profile-id',s.get('measurement',{}).get('profile_id')=='rgi.ext02a.hardware-source-audit.v1'),
 ('evidence-profile-hash',ext.get('profile_sha256')==ph),
 ('architecture',ext.get('architecture')==z.arch),
 ('native-kernel',bool(ext.get('native_kernel'))),
 ('elapsed-positive',ext.get('native_vector_result',{}).get('elapsed_ns',0)>0),
 ('checksum-finite',isinstance(ext.get('native_vector_result',{}).get('checksum'),(int,float)))
]
result={'subject':z.subject,'architecture':z.arch,'profile_sha256':ph,'pass_count':sum(v for _,v in checks),'total':len(checks),'status':'PASS' if all(v for _,v in checks) else 'FAIL','checks':[{'name':n,'pass':v} for n,v in checks],'state':s,'capabilities':c}
Path(z.out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':result['status'],'pass_count':result['pass_count'],'total':result['total'],'profile_sha256':ph},sort_keys=True));raise SystemExit(0 if result['status']=='PASS' else 2)

#!/usr/bin/env python3
import argparse,base64,json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

a=argparse.ArgumentParser();a.add_argument('--receipt',required=True);a.add_argument('--probe',required=True);a.add_argument('--role',required=True);a.add_argument('--out',required=True);z=a.parse_args()
r=json.loads(Path(z.receipt).read_text());p=json.loads(Path(z.probe).read_text())
payload=base64.b64decode(r['signed_payload_base64']);pub=base64.b64decode(r['public_key_base64']);sig=base64.b64decode(r['signature_base64'])
sig_ok=True
try: Ed25519PublicKey.from_public_bytes(pub).verify(sig,payload)
except Exception: sig_ok=False
sid=p['state']['state_id'];field='x64_state_id' if z.role=='x64' else 'arm64_state_id'
checks={
 'signature':sig_ok,
 'result':r.get('result')=='REAL_HARDWARE_TYPED_REFUSAL_INTEROPERABILITY_PASS',
 'profile':r.get('profile_sha256')==p.get('profile_sha256'),
 'state_binding':r.get(field)==sid,
 'probe_pass':p.get('status')=='PASS' and p.get('pass_count')==p.get('total'),
 'unknown':p.get('state',{}).get('status')=='UNKNOWN',
 'theta_absent':'brodzinski' not in p.get('state',{})
}
out={'trial':'RGI-EXT-02A','role':z.role,'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'evaluator_result':r.get('result'),'profile_sha256':r.get('profile_sha256'),'state_id':sid}
Path(z.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 2)

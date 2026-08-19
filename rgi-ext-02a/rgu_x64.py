#!/usr/bin/env python3
import json, hashlib, os, platform, subprocess, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
from pathlib import Path

PROFILE_PATH=Path(os.environ.get('PROFILE','rgi-ext-02a/profile.json'))
VECTOR_PATH=Path(os.environ.get('VECTOR_RESULT','evidence/vector.json'))
PROFILE_BYTES=PROFILE_PATH.read_bytes(); PROFILE=json.loads(PROFILE_BYTES); PROFILE_SHA=hashlib.sha256(PROFILE_BYTES).hexdigest()
VECTOR=json.loads(VECTOR_PATH.read_text())
HARDWARE={
  'platform':platform.platform(), 'machine':platform.machine(), 'processor':platform.processor(),
  'cpu_count':os.cpu_count(), 'uname':' '.join(platform.uname()),
  'lscpu':subprocess.check_output(['lscpu'],text=True)
}
ENV_HASH=hashlib.sha256(json.dumps({'profile_sha256':PROFILE_SHA,'hardware':HARDWARE,'vector':VECTOR},sort_keys=True).encode()).hexdigest()
SUBJECT=os.environ.get('SUBJECT_ID','ext02a-x64-node')
NOW=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
STATE={
 'spec_version':'0.1.0','state_id':str(uuid.uuid5(uuid.NAMESPACE_URL,'rgi-ext02a:'+ENV_HASH)),'observed_at':NOW,
 'producer':{'id':'rgu://ext02a/x64-python','implementation':'rgi-ext02a-x64-python','version':'1.0.0','conformance':['BS-CORE-PRODUCER-0.1','BS-RGU-PRODUCER-0.1','RGI-RGU-1.0']},
 'subject':{'id':SUBJECT,'type':'compute-node','scope':'node'},'status':'UNKNOWN',
 'resources':{'primary':{'id':'bs.compute.cpu.capacity','unit':'{cpu}','boundary':'UPPER','role':'PRIMARY'},'coupled':[]},
 'observability':{'status':'UNMEASURED','reason_code':'MEASUREMENT_NOT_EXECUTED'},
 'measurement':{'method_id':'bs.method.source_audit.v0.1','profile_id':'rgi.ext02a.hardware-source-audit.v1','decoder_fidelity':'NOT_APPLICABLE','outcome_interface':'NATIVE'},
 'chart':{'id':'rgi.ext02a.cpu.vector-concurrency','version':'1','source':'PROFILE_DEFINED','status':'CERTIFIED'},
 'reason':{'code':'MEASUREMENT_NOT_EXECUTED','message':'Real x64 hardware source audit and native vector workload completed; no validated alpha/beta measurement profile exists for this target, so no Brodzinski Number is emitted.'},
 'extensions':{'org.resourcegeometry.ext02a':{'profile_sha256':PROFILE_SHA,'environment_sha256':ENV_HASH,'architecture':'x86_64','native_kernel':VECTOR['kernel'],'native_vector_result':VECTOR,'hardware':HARDWARE}}
}
CAPS={'rgi_version':'1.0.0','implementation':{'id':'rgi-ext02a-x64-python','language':'Python'},'operator':{'organization_id':'github-hosted-ext02a-x64'},'bs_core_compatibility':'BS-CORE-1.0-COMPAT','conformance_claims':['BS-RGU-PRODUCER-0.1','RGI-RGU-1.0'],'benchmark_profiles':[{'profile_id':PROFILE['profile_id'],'version':PROFILE['version'],'sha256':PROFILE_SHA}],'certification_bundle_versions':['rgi-certification-bundle/1.0']}

class H(BaseHTTPRequestHandler):
 def sendj(self,obj,code=200):
  b=json.dumps(obj,sort_keys=True).encode(); self.send_response(code); self.send_header('content-type','application/json'); self.send_header('content-length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def log_message(self,*a): pass
 def do_GET(self):
  if self.path=='/healthz': return self.sendj({'status':'ok'})
  if self.path=='/rgi/v1/capabilities': return self.sendj(CAPS)
  if self.path==f"/rgi/v1/benchmark-profiles/{PROFILE['profile_id']}/{PROFILE['version']}": return self.sendj(PROFILE)
  if self.path==f'/rgi/v1/states/{SUBJECT}': return self.sendj(STATE)
  return self.sendj({'error':'NOT_FOUND'},404)

if __name__=='__main__':
 port=int(os.environ.get('PORT','38191')); print(json.dumps({'profile_sha256':PROFILE_SHA,'environment_sha256':ENV_HASH,'subject':SUBJECT,'state_id':STATE['state_id']},sort_keys=True),flush=True); HTTPServer(('127.0.0.1',port),H).serve_forever()

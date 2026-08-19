import json, hashlib, os
from pathlib import Path

apple=json.loads(Path('apple/APPLE_METAL_PREFLIGHT.json').read_text())
linux=json.loads(Path('linux/LINUX_CGROUP_PREFLIGHT.json').read_text())

def h(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

apple_ok = bool(apple.get('metal_available')) and apple.get('max_buffer_length',0)>0 and apple.get('recommended_max_working_set_size',0)>0 and len(apple.get('allocated_buffer_sizes',[]))>=4
linux_ok = bool(linux.get('cgroup_v2')) and bool(linux.get('resource_boundary_observable')) and all(linux.get('controller_files_present',{}).get(k) for k in ['memory.max','memory.current','memory.events']) and sum(1 for r in linux.get('allocation_probe',[]) if r.get('status')=='PASS')>=4

receipt={
 'trial':'RGI-EXT-02',
 'stage':'REAL_INFRASTRUCTURE_NATIVE_PREFLIGHT',
 'apple_target':{
   'class':'APPLE_METAL_ACCELERATOR',
   'eligible_for_measurement_design':apple_ok,
   'device_name':apple.get('device_name'),
   'has_unified_memory':apple.get('has_unified_memory'),
   'max_buffer_length':apple.get('max_buffer_length'),
   'recommended_max_working_set_size':apple.get('recommended_max_working_set_size'),
   'artifact_sha256':h('apple/APPLE_METAL_PREFLIGHT.json')
 },
 'linux_target':{
   'class':'LINUX_CGROUP_V2_MEMORY_CONTROLLER',
   'eligible_for_measurement_design':linux_ok,
   'memory_max_raw':linux.get('memory_max_raw'),
   'memory_max_bytes':linux.get('memory_max_bytes'),
   'artifact_sha256':h('linux/LINUX_CGROUP_PREFLIGHT.json')
 },
 'theta_estimated':False,
 'brodzinski_state_certified':False,
 'promotion_rule':'PROMOTE_TO_FROZEN_MEASUREMENT_DESIGN_ONLY_IF_BOTH_TARGETS_ELIGIBLE',
 'result':'PREFLIGHT_PASS' if apple_ok and linux_ok else 'PREFLIGHT_STOP'
}
Path('RGI_EXT_02_PREFLIGHT_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
Path('RGI_EXT_02_PREFLIGHT_REPORT.md').write_text(
  '# RGI-EXT-02 Real Infrastructure Native Preflight\n\n'
  f"Result: **{receipt['result']}**\n\n"
  f"Apple Metal eligible: **{apple_ok}**; device: `{apple.get('device_name')}`; maxBufferLength: `{apple.get('max_buffer_length')}`; recommendedMaxWorkingSetSize: `{apple.get('recommended_max_working_set_size')}`.\n\n"
  f"Linux cgroup-v2 eligible: **{linux_ok}**; memory.max: `{linux.get('memory_max_raw')}`.\n\n"
  'No Brodzinski Number was estimated in preflight. No certification claim was issued.\n'
)
print(json.dumps(receipt,indent=2,sort_keys=True))
if receipt['result']!='PREFLIGHT_PASS': raise SystemExit(2)

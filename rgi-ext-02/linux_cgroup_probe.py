import json, os, platform, time, hashlib
from pathlib import Path

CG = Path('/sys/fs/cgroup')
def read(name):
    p = CG / name
    try:
        return p.read_text().strip()
    except Exception as e:
        return None

def parse_int(v):
    if v is None or v == 'max': return None
    try: return int(v)
    except: return None

before = parse_int(read('memory.current'))
limit_raw = read('memory.max')
limit = parse_int(limit_raw)
high_raw = read('memory.high')
high = parse_int(high_raw)
events_before = read('memory.events')

sizes = [1<<20, 4<<20, 16<<20, 64<<20, 128<<20, 256<<20, 512<<20]
results=[]
for size in sizes:
    t0=time.perf_counter_ns()
    try:
        b=bytearray(size)
        page=4096
        for i in range(0,size,page): b[i]=1
        elapsed=time.perf_counter_ns()-t0
        cur=parse_int(read('memory.current'))
        results.append({'bytes':size,'status':'PASS','elapsed_ns':elapsed,'memory_current':cur})
        del b
    except MemoryError:
        results.append({'bytes':size,'status':'MEMORY_ERROR','elapsed_ns':time.perf_counter_ns()-t0,'memory_current':parse_int(read('memory.current'))})
        break

time.sleep(0.2)
after=parse_int(read('memory.current'))
probe={
  'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
  'platform': platform.platform(),
  'machine': platform.machine(),
  'processor': platform.processor(),
  'cpu_count': os.cpu_count(),
  'cgroup_v2': (CG/'cgroup.controllers').exists(),
  'memory_max_raw': limit_raw,
  'memory_max_bytes': limit,
  'memory_high_raw': high_raw,
  'memory_high_bytes': high,
  'memory_current_before': before,
  'memory_current_after': after,
  'memory_events_before': events_before,
  'memory_events_after': read('memory.events'),
  'allocation_probe': results,
  'resource_boundary_observable': limit_raw is not None,
  'controller_files_present': {n:(CG/n).exists() for n in ['memory.max','memory.current','memory.events','memory.high','memory.stat']}
}
print(json.dumps(probe,indent=2,sort_keys=True))

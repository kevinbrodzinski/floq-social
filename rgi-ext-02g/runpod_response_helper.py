#!/usr/bin/env python3
"""EXT-02G.1 response collector for the exact last native carrier workload."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

STATE = Path(os.environ.get("RGI_EXT02G_NATIVE_STATE_DIR", "/workspace/rgi-ext-02g-native"))


def refuse(reason, detail=None):
    out = {"status": "REFUSED", "reason": reason}
    if detail:
        out["detail"] = str(detail)
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(2)


if len(sys.argv) != 2 or not sys.argv[1].strip():
    refuse("EXECUTION_RECEIPT_ID_REQUIRED")
execution_receipt_id = sys.argv[1].strip()

p = STATE / "last_workload.json"
if not p.exists():
    refuse("NATIVE_WORKLOAD_STATE_NOT_FOUND")

raw = p.read_bytes()
try:
    workload = json.loads(raw)
except Exception as exc:
    refuse("NATIVE_WORKLOAD_STATE_INVALID", repr(exc))
if workload.get("status") != "PASS":
    refuse("NATIVE_WORKLOAD_STATE_NOT_PASS")

try:
    smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=uuid,name,pci.bus_id,driver_version,memory.total,memory.free,memory.used", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, timeout=15
    )
    native_snapshot = smi.stdout.strip().splitlines()[0] if smi.returncode == 0 and smi.stdout.strip() else None
except Exception:
    native_snapshot = None

out = {
    "status": "PASS",
    "requested_execution_receipt_id": execution_receipt_id,
    "native_workload_payload_sha256": hashlib.sha256(raw).hexdigest(),
    "workload": workload,
    "native_post_execution_snapshot": native_snapshot,
    "collected_at_ns": time.time_ns(),
    "claim_boundary": "Response lineage for one carrier execution only; no Resource Geometry scientific inference performed.",
}
print(json.dumps(out, sort_keys=True))

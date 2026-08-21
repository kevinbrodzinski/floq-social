#!/usr/bin/env python3
"""EXT-02G.1 one-shot carrier workload for an NVIDIA GPU.

The requested resource level p is interpreted as a normalized fraction of native
GPU device-memory capacity. The allocation is rounded down to the CUDA-native
minimum allocation granularity and touched on-device. A fixed CUDA matrix
multiply is then executed to prove native compute execution. This helper does
not perform Resource Geometry estimation.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

STATE = Path(os.environ.get("RGI_EXT02G_NATIVE_STATE_DIR", "/workspace/rgi-ext-02g-native"))
STATE.mkdir(parents=True, exist_ok=True)


def emit_refusal(reason, detail=None):
    out = {"status": "REFUSED", "reason": reason}
    if detail:
        out["detail"] = str(detail)
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(2)


if len(sys.argv) != 2:
    emit_refusal("RESOURCE_LEVEL_ARGUMENT_REQUIRED")

try:
    p = float(sys.argv[1])
except Exception:
    emit_refusal("INVALID_RESOURCE_LEVEL")
if not (0.0 < p < 1.0):
    emit_refusal("RESOURCE_LEVEL_OUT_OF_RANGE", p)

try:
    import torch
except Exception as exc:
    emit_refusal("PYTORCH_UNAVAILABLE", repr(exc))

if not torch.cuda.is_available():
    emit_refusal("CUDA_RUNTIME_GPU_UNAVAILABLE")

helper = Path(__file__).with_name("runpod_quantum_helper.py")
qrun = subprocess.run([sys.executable, str(helper)], text=True, capture_output=True)
try:
    qobj = json.loads(qrun.stdout.strip())
except Exception:
    emit_refusal("NATIVE_QUANTUM_HELPER_NONJSON", qrun.stderr[-1000:])
if qrun.returncode != 0 or qobj.get("status") != "PASS":
    emit_refusal("NATIVE_QUANTUM_HELPER_FAILED", qobj)
quantum = int(qobj["quantum"])
if quantum <= 0:
    emit_refusal("INVALID_NATIVE_QUANTUM", quantum)

try:
    torch.cuda.set_device(0)
    props = torch.cuda.get_device_properties(0)
    total = int(props.total_memory)
    requested_unaligned = int(math.floor(p * total))
    requested = (requested_unaligned // quantum) * quantum
    if requested < quantum:
        requested = quantum
    if requested >= total:
        emit_refusal("REQUESTED_ALLOCATION_EXCEEDS_NATIVE_CAPACITY", requested)

    torch.cuda.empty_cache()
    before_alloc = int(torch.cuda.memory_allocated(0))
    before_reserved = int(torch.cuda.memory_reserved(0))

    t0 = time.perf_counter_ns()
    buf = torch.empty(requested, dtype=torch.uint8, device="cuda")
    buf.fill_(0x5A)

    # Fixed native compute proof. Keep it modest so this remains a carrier
    # admission, not a scientific measurement sweep.
    n = 1024
    a = torch.arange(n * n, dtype=torch.float32, device="cuda").reshape(n, n)
    b = torch.full((n, n), 1.0 / n, dtype=torch.float32, device="cuda")
    start_evt = torch.cuda.Event(enable_timing=True)
    end_evt = torch.cuda.Event(enable_timing=True)
    start_evt.record()
    c = a @ b
    end_evt.record()
    torch.cuda.synchronize()
    t1 = time.perf_counter_ns()

    elapsed_ms = float(start_evt.elapsed_time(end_evt))
    checksum = float(c[0, 0].item() + c[-1, -1].item())
    touched = int(buf[0].item()) + int(buf[-1].item())

    after_alloc = int(torch.cuda.memory_allocated(0))
    after_reserved = int(torch.cuda.memory_reserved(0))

    try:
        smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,name,memory.total,memory.used", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=15
        )
        smi_row = smi.stdout.strip().splitlines()[0] if smi.returncode == 0 and smi.stdout.strip() else None
    except Exception:
        smi_row = None

    payload = {
        "status": "PASS",
        "workload_id": "RGI_EXT_02G1_CARRIER_MEMORY_PLUS_MATMUL_V1",
        "resource_coordinate": "GPU_DEVICE_MEMORY_FRACTION",
        "requested_resource_level": p,
        "native_capacity_bytes": total,
        "native_quantum_bytes": quantum,
        "requested_bytes_unaligned": requested_unaligned,
        "requested_bytes_aligned": requested,
        "realized_fraction": requested / total,
        "torch_memory_allocated_before": before_alloc,
        "torch_memory_allocated_after": after_alloc,
        "torch_memory_reserved_before": before_reserved,
        "torch_memory_reserved_after": after_reserved,
        "device_name": str(props.name),
        "compute_capability": [int(props.major), int(props.minor)],
        "matmul_shape": [n, n],
        "cuda_event_elapsed_ms": elapsed_ms,
        "wall_elapsed_ns": t1 - t0,
        "compute_checksum": checksum,
        "memory_touch_checksum": touched,
        "nvidia_smi_snapshot": smi_row,
        "native_quantum_receipt": qobj,
        "claim_boundary": "One native carrier workload only; no alpha, beta, Theta, class, contact, or certification computed.",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    (STATE / "last_workload.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))
except SystemExit:
    raise
except torch.cuda.OutOfMemoryError as exc:
    emit_refusal("NATIVE_GPU_ALLOCATION_FAILED", repr(exc))
except Exception as exc:
    emit_refusal("GPU_WORKLOAD_EXCEPTION", repr(exc))

#!/usr/bin/env python3
"""EXT-02G.1 native-quantum helper for NVIDIA RunPod targets.

Reports the minimum physical-allocation granularity exposed by the CUDA Driver
virtual-memory API. This is an execution-carrier fact only; it does not estimate
alpha, beta, Theta, a Brodzinski Class, or a certified Brodzinski State.
"""
import json
import sys


def fail(reason, detail=None):
    out = {"status": "REFUSED", "reason": reason, "native_source": "CUDA_DRIVER_cuMemGetAllocationGranularity"}
    if detail:
        out["detail"] = str(detail)
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(2)


try:
    try:
        from cuda import cuda as cu  # cuda-python 11.x/12.x
        binding = "cuda-python:cuda.cuda"
    except Exception:
        from cuda.bindings import driver as cu  # newer cuda-bindings
        binding = "cuda.bindings.driver"
except Exception as exc:
    fail("CUDA_PYTHON_BINDING_UNAVAILABLE", exc)


def ok(result):
    try:
        return int(result) == 0
    except Exception:
        return str(result).endswith("CUDA_SUCCESS")


try:
    init = cu.cuInit(0)
    if not init or not ok(init[0]):
        fail("CUDA_DRIVER_INIT_FAILED", init[0] if init else "empty result")

    got = cu.cuDeviceGet(0)
    if len(got) < 2 or not ok(got[0]):
        fail("CUDA_DEVICE_GET_FAILED", got[0] if got else "empty result")
    dev = got[1]

    prop = cu.CUmemAllocationProp()
    prop.type = cu.CUmemAllocationType.CU_MEM_ALLOCATION_TYPE_PINNED
    prop.location.type = cu.CUmemLocationType.CU_MEM_LOCATION_TYPE_DEVICE
    prop.location.id = int(dev)

    minimum_result = cu.cuMemGetAllocationGranularity(
        prop, cu.CUmemAllocationGranularity_flags.CU_MEM_ALLOC_GRANULARITY_MINIMUM
    )
    if len(minimum_result) < 2 or not ok(minimum_result[0]):
        fail("CUDA_MINIMUM_GRANULARITY_QUERY_FAILED", minimum_result[0] if minimum_result else "empty result")
    minimum = int(minimum_result[1])

    recommended_result = cu.cuMemGetAllocationGranularity(
        prop, cu.CUmemAllocationGranularity_flags.CU_MEM_ALLOC_GRANULARITY_RECOMMENDED
    )
    recommended = None
    if len(recommended_result) >= 2 and ok(recommended_result[0]):
        recommended = int(recommended_result[1])

    if minimum <= 0:
        fail("CUDA_NONPOSITIVE_NATIVE_GRANULARITY", minimum)

    out = {
        "status": "PASS",
        "quantum": minimum,
        "unit": "bytes",
        "recommended_quantum": recommended,
        "device_ordinal": int(dev),
        "native_source": "CUDA_DRIVER_cuMemGetAllocationGranularity",
        "binding": binding,
        "claim_boundary": "Native CUDA allocation granularity only; no Resource Geometry scientific estimator executed.",
    }
    print(json.dumps(out, sort_keys=True))
except SystemExit:
    raise
except Exception as exc:
    fail("CUDA_NATIVE_QUANTUM_EXCEPTION", repr(exc))
